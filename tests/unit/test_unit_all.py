import json
import pathlib
import sys
import types

import pytest

# Make "app/" importable (so imports like "from utils.messaging import ..." work)
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
sys.path.insert(0, str(APP_DIR))

import app.agents.behavior_and_alarm.behavior_and_alarm_agent_behaviour as alarm_mod  # noqa: E402
import app.agents.feed_control.behaviour as feed_behaviour_mod  # noqa: E402
import app.agents.lighting.lighting_agent_behaviour as lighting_mod  # noqa: E402
from app.agents.behavior_and_alarm.behavior_and_alarm_agent_behaviour import (  # noqa: E402
    ReceiveBehaviour as AlarmReceiveBehaviour,
)
from app.agents.feed_control.behaviour import (  # noqa: E402
    ReceiveBehaviour as FeedReceiveBehaviour,
)
from app.agents.hen_simulator.behaviour import SimulateBehaviour  # noqa: E402
from app.agents.lighting.lighting_agent_behaviour import (  # noqa: E402
    LightningBehaviour,
)
from app.models.environment_state import FeedState  # noqa: E402
from app.models.hen_state import HenState  # noqa: E402
from app.utils.config_loader import get_agent_credentials  # noqa: E402
from app.utils.messaging import build_message, parse_content  # noqa: E402


# -------------------------
# Helpers
# -------------------------
class DummyJID:
    def __init__(self, jid: str):
        self.jid = jid

    def __str__(self) -> str:
        return self.jid


class DummyAgent:
    """Minimal agent-like object: behaviours access attrs on self.agent."""

    def __init__(self, jid: str = "dummy@localhost"):
        self.jid = DummyJID(jid)


@pytest.fixture
def sent_messages_collector():
    return []


def attach_async_send(behaviour, sent_messages_collector):
    async def _send(msg):
        sent_messages_collector.append(msg)

    behaviour.send = _send  # monkeypatch method directly


# -------------------------
# utils.messaging
# -------------------------
def test_build_message_sets_metadata_and_body():
    msg = build_message(
        to="someone@localhost",
        performative="inform",
        conversation="update_state",
        content={"type": "ping", "payload": {"x": 1}},
    )

    assert msg.to == "someone@localhost"
    assert msg.get_metadata("performative") == "inform"
    assert msg.get_metadata("conversation") == "update_state"
    assert msg.get_metadata("language") == "json"
    assert msg.get_metadata("ontology") == "hen_house"
    assert json.loads(msg.body) == {"type": "ping", "payload": {"x": 1}}


def test_parse_content_empty_body_returns_empty_dict():
    msg = build_message(
        to="someone@localhost",
        performative="inform",
        conversation="update_state",
        content={"type": "x"},
    )
    msg.body = ""
    assert parse_content(msg) == {}


def test_parse_content_invalid_json_returns_raw():
    msg = build_message(
        to="someone@localhost",
        performative="inform",
        conversation="update_state",
        content={"type": "x"},
    )
    msg.body = "{not-json"
    assert parse_content(msg) == {"raw": "{not-json"}


# -------------------------
# utils.config_loader
# -------------------------
def test_get_agent_credentials_from_cfg_dict():
    cfg = {
        "agents": {
            "feed_control": {"jid": "feed@localhost", "password": "123"},
            "ui_agent": {"jid": "ui@localhost", "password": "abc"},
        }
    }
    jid, pwd = get_agent_credentials("feed_control", cfg=cfg)
    assert jid == "feed@localhost"
    assert pwd == "123"


# -------------------------
# FeedControlAgent behaviour (unit)
# -------------------------
@pytest.mark.asyncio
async def test_feed_control_batch_feeding_happy_path(monkeypatch, sent_messages_collector):
    # Arrange dummy agent state
    agent = DummyAgent("feedcontrol@localhost")
    agent.feed_state = FeedState(level=10, capacity=100)
    agent.hunger_threshold = 60
    agent.max_hens_per_batch = 2
    agent.feed_cooldown_s = 0.0
    agent.portion_size = 4
    agent.low_feed_threshold = 2

    agent.ui_jid = "ui@localhost"
    agent.logger_jid = "logger@localhost"
    agent.behavior_alarm_jid = "alarm@localhost"

    agent.last_hunger = {
        "simulator1@localhost": 80,
        "simulator2@localhost": 70,
        "simulator3@localhost": 65,
    }
    agent.last_fed_at = {}

    beh = FeedReceiveBehaviour()
    beh.agent = agent
    attach_async_send(beh, sent_messages_collector)

    # Make time deterministic
    monkeypatch.setattr(feed_behaviour_mod, "_now", lambda: 100.0)

    # Act
    await beh.handle_batch_feeding()

    # Assert: max_hens_per_batch=2 => feed 2 hens with highest hunger
    assert agent.feed_state.level == 2  # 10 - 4 - 4

    # Check that feed messages were sent to hens
    sent_conv_types = [
        (m.get_metadata("conversation"), json.loads(m.body).get("type")) for m in sent_messages_collector
    ]
    assert ("feeding", "feed_dispensed") in sent_conv_types
    assert ("update_state", "feed_dispensed") in sent_conv_types
    assert ("update_state", "feed_state_update") in sent_conv_types
    assert ("logging", "log_event") in sent_conv_types

    # Since remaining_feed <= low_feed_threshold (2 <= 2), warning should be sent
    assert ("alerts", "low_feed_warning") in sent_conv_types


@pytest.mark.asyncio
async def test_feed_control_respects_cooldown(monkeypatch, sent_messages_collector):
    agent = DummyAgent("feedcontrol@localhost")
    agent.feed_state = FeedState(level=10, capacity=100)
    agent.hunger_threshold = 60
    agent.max_hens_per_batch = 3
    agent.feed_cooldown_s = 999.0  # huge cooldown
    agent.portion_size = 4
    agent.low_feed_threshold = 0

    agent.ui_jid = "ui@localhost"
    agent.logger_jid = "logger@localhost"
    agent.behavior_alarm_jid = "alarm@localhost"

    agent.last_hunger = {"simulator1@localhost": 90}
    agent.last_fed_at = {"simulator1@localhost": 100.0}  # already fed "now"

    beh = FeedReceiveBehaviour()
    beh.agent = agent
    attach_async_send(beh, sent_messages_collector)
    monkeypatch.setattr(feed_behaviour_mod, "_now", lambda: 100.5)

    await beh.handle_batch_feeding()

    # No feeding due to cooldown
    assert agent.feed_state.level == 10
    sent_conv_types = [
        (m.get_metadata("conversation"), json.loads(m.body).get("type")) for m in sent_messages_collector
    ]
    assert ("feeding", "feed_dispensed") not in sent_conv_types


@pytest.mark.asyncio
async def test_feed_control_no_feed_alert_when_empty(sent_messages_collector):
    agent = DummyAgent("feedcontrol@localhost")
    agent.feed_state = FeedState(level=0, capacity=100)
    agent.hunger_threshold = 60
    agent.max_hens_per_batch = 2
    agent.feed_cooldown_s = 0.0
    agent.portion_size = 4
    agent.low_feed_threshold = 2

    agent.ui_jid = "ui@localhost"
    agent.logger_jid = "logger@localhost"
    agent.behavior_alarm_jid = "alarm@localhost"

    agent.last_hunger = {
        "simulator1@localhost": 80,  # should trigger no_feed
        "simulator2@localhost": 30,  # ignored
    }
    agent.last_fed_at = {}

    beh = FeedReceiveBehaviour()
    beh.agent = agent
    attach_async_send(beh, sent_messages_collector)

    await beh.handle_batch_feeding()

    sent_conv_types = [
        (m.get_metadata("conversation"), json.loads(m.body).get("type")) for m in sent_messages_collector
    ]
    # alert no_feed should be sent
    assert ("alerts", "no_feed") in sent_conv_types
    # feed_state_update should broadcast reason=no_feed
    assert ("update_state", "feed_state_update") in sent_conv_types


# -------------------------
# LightingAgent behaviour (unit)
# -------------------------
def test_lighting_compute_target_in_range_returns_neutral():
    agent = DummyAgent("lighting@localhost")
    agent.neutral_level = 50
    agent.min_level = 0
    agent.max_level = 100
    agent.target_aggr_min = -3
    agent.target_aggr_max = 3
    agent.gain_per_aggression = 4.0

    beh = LightningBehaviour()
    beh.agent = agent

    assert beh._compute_target_level(aggression=0) == 50
    assert beh._compute_target_level(aggression=3) == 50
    assert beh._compute_target_level(aggression=-3) == 50


def test_lighting_compute_target_out_of_range_clamped():
    agent = DummyAgent("lighting@localhost")
    agent.neutral_level = 50
    agent.min_level = 0
    agent.max_level = 100
    agent.target_aggr_min = -3
    agent.target_aggr_max = 3
    agent.gain_per_aggression = 10.0

    beh = LightningBehaviour()
    beh.agent = agent

    # aggression positive => up, but clamp to max=100
    assert beh._compute_target_level(aggression=10) == 100
    # aggression negative => down, clamp to min=0
    assert beh._compute_target_level(aggression=-10) == 0


def test_lighting_allow_send_respects_min_interval_and_min_delta(monkeypatch):
    agent = DummyAgent("lighting@localhost")
    agent.neutral_level = 50
    agent.min_update_interval_s = 10.0
    agent.min_delta_to_send = 2
    agent.hen_light_levels = {"simulator1@localhost": 50}
    agent._last_set_at = {"simulator1@localhost": 100.0}

    beh = LightningBehaviour()
    beh.agent = agent

    # too soon -> False
    monkeypatch.setattr(lighting_mod.time, "monotonic", lambda: 105.0)
    assert beh._allow_send("simulator1@localhost", new_level=60) is False

    # after interval but delta too small -> False
    monkeypatch.setattr(lighting_mod.time, "monotonic", lambda: 200.0)
    assert beh._allow_send("simulator1@localhost", new_level=51) is False

    # after interval + big delta -> True
    assert beh._allow_send("simulator1@localhost", new_level=60) is True


# -------------------------
# HenSimulator light effect (unit)
# -------------------------
def test_hen_simulator_light_effect_direction_and_clamp():
    agent = DummyAgent("simulator1@localhost")
    agent.current_light_level = 70
    agent.neutral_light_level = 50
    agent.light_sensitivity = 10
    agent.max_light_effect_per_tick = 2

    beh = SimulateBehaviour(period=5)
    beh.agent = agent

    # level 70 > neutral 50 => delta = -20 => sign = -1 => negative effect (reduces aggression)
    eff = beh._compute_light_effect_on_aggression()
    assert eff <= 0
    assert eff >= -2

    agent.current_light_level = 30  # below neutral => positive effect
    eff2 = beh._compute_light_effect_on_aggression()
    assert eff2 >= 0
    assert eff2 <= 2


# -------------------------
# BehaviorAndAlarm throttling & critical events (unit)
# -------------------------
@pytest.mark.asyncio
async def test_alarm_throttles_aggression_update(monkeypatch, sent_messages_collector):
    agent = DummyAgent("alarm@localhost")
    agent.ui_jid = "ui@localhost"
    agent.logger_jid = "logger@localhost"
    agent.lighting_jid = "lighting@localhost"

    agent.max_abs_aggression = 10
    agent.aggression_threshold = 7
    agent.regulate_min_interval_sec = 5.0
    agent.aggression_target_min = -3
    agent.aggression_target_max = 3

    beh = AlarmReceiveBehaviour()
    beh.agent = agent
    attach_async_send(beh, sent_messages_collector)

    # deterministic time
    t = {"now": 100.0}
    monkeypatch.setattr(alarm_mod.time, "monotonic", lambda: t["now"])

    content = {"hen_id": "simulator1@localhost", "aggression": 5, "hunger": 20}

    await beh.handle_behavior_message(content)
    # second call within interval => should not send another aggression_update
    t["now"] = 102.0
    await beh.handle_behavior_message(content)

    sent_types = [
        json.loads(m.body).get("type") for m in sent_messages_collector if m.get_metadata("conversation") == "lighting"
    ]
    assert sent_types.count("aggression_update") == 1


@pytest.mark.asyncio
async def test_alarm_raises_critical_event_when_threshold_exceeded(sent_messages_collector):
    agent = DummyAgent("alarm@localhost")
    agent.ui_jid = "ui@localhost"
    agent.logger_jid = "logger@localhost"
    agent.lighting_jid = "lighting@localhost"

    agent.max_abs_aggression = 10
    agent.aggression_threshold = 7
    agent.regulate_min_interval_sec = 0.0
    agent.aggression_target_min = -3
    agent.aggression_target_max = 3

    beh = AlarmReceiveBehaviour()
    beh.agent = agent
    attach_async_send(beh, sent_messages_collector)

    await beh.handle_behavior_message({"hen_id": "simulator1@localhost", "aggression": 9, "hunger": 80})

    sent_conv_types = [
        (m.get_metadata("conversation"), json.loads(m.body).get("type")) for m in sent_messages_collector
    ]
    assert ("update_state", "critical_event") in sent_conv_types
    assert ("logging", "log_event") in sent_conv_types
    assert ("lighting", "aggression_update") in sent_conv_types
