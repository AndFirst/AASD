# tests/integration/test_integration_all.py
import json
import pathlib
import sys

import pytest

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
from app.agents.hen_simulator.behaviour import (  # noqa: E402
    ReceiveFeedingBehaviour,
    ReceiveLightingBehaviour,
    SimulateBehaviour,
)
from app.agents.lighting.lighting_agent_behaviour import (  # noqa: E402
    LightningBehaviour,
)
from app.models.environment_state import FeedState  # noqa: E402
from app.models.hen_state import HenState  # noqa: E402
from app.utils.messaging import build_message, parse_content  # noqa: E402


class DummyJID:
    def __init__(self, jid: str):
        self.jid = jid

    def __str__(self) -> str:
        return self.jid


class DummyAgent:
    def __init__(self, jid: str):
        self.jid = DummyJID(jid)


def make_send_collector(collector):
    async def _send(msg):
        collector.append(msg)

    return _send


@pytest.mark.asyncio
async def test_integration_aggression_to_light_to_hen(monkeypatch):
    """
    End-to-end (offline):
    BehaviorAndAlarmAgent -> LightingAgent -> HenSimulator (lighting receive)
    """
    sent_alarm = []
    sent_lighting = []
    sent_hen = []

    # --- Alarm agent + behaviour ---
    alarm_agent = DummyAgent("alarm@localhost")
    alarm_agent.ui_jid = "ui@localhost"
    alarm_agent.logger_jid = "logger@localhost"
    alarm_agent.lighting_jid = "lighting@localhost"
    alarm_agent.max_abs_aggression = 10
    alarm_agent.aggression_threshold = 7
    alarm_agent.regulate_min_interval_sec = 0.0
    alarm_agent.aggression_target_min = -3
    alarm_agent.aggression_target_max = 3

    alarm_beh = AlarmReceiveBehaviour()
    alarm_beh.agent = alarm_agent
    alarm_beh.send = make_send_collector(sent_alarm)

    # --- Lighting agent + behaviour ---
    lighting_agent = DummyAgent("lighting@localhost")
    lighting_agent.ui_jid = "ui@localhost"
    lighting_agent.logger_jid = "logger@localhost"
    lighting_agent.neutral_level = 50
    lighting_agent.min_level = 0
    lighting_agent.max_level = 100
    lighting_agent.target_aggr_min = -3
    lighting_agent.target_aggr_max = 3
    lighting_agent.gain_per_aggression = 4.0
    lighting_agent.min_update_interval_s = 0.0
    lighting_agent.min_delta_to_send = 0
    lighting_agent.hen_light_levels = {"simulator1@localhost": 50}

    light_beh = LightningBehaviour()
    light_beh.agent = lighting_agent
    light_beh.send = make_send_collector(sent_lighting)

    # --- Hen agent + lighting-receive behaviour ---
    hen_agent = DummyAgent("simulator1@localhost")
    hen_agent.hen_id = "simulator1@localhost"
    hen_agent.state = HenState(hunger=10, aggression=0)
    hen_agent.current_light_level = 50

    hen_light_recv = ReceiveLightingBehaviour()
    hen_light_recv.agent = hen_agent
    hen_light_recv.send = make_send_collector(sent_hen)  # not used, but ok

    # Act: alarm handles high aggression and should send aggression_update to lighting
    await alarm_beh.handle_behavior_message({"hen_id": "simulator1@localhost", "aggression": 9, "hunger": 80})

    # Extract the aggression_update message
    lighting_msgs = [m for m in sent_alarm if m.get_metadata("conversation") == "lighting"]
    assert lighting_msgs, "Alarm should send at least one lighting/aggression_update message"
    msg_to_lighting = lighting_msgs[0]
    content = parse_content(msg_to_lighting)
    assert content["type"] == "aggression_update"

    # Feed it into LightingBehaviour handler directly
    await light_beh._handle_aggression_update(content["payload"])

    # Lighting should broadcast light_level_update to hen
    hen_msgs = [m for m in sent_lighting if m.get_metadata("conversation") == "lighting"]
    assert hen_msgs, "Lighting should send lighting/light_level_update to hen"
    msg_to_hen = hen_msgs[0]

    # Now deliver to Hen's ReceiveLightingBehaviour by mocking receive()
    async def fake_receive(timeout=1):
        return msg_to_hen

    hen_light_recv.receive = fake_receive
    await hen_light_recv.run()

    # Assert: hen light level changed away from neutral for high aggression (should go up, because gain*aggr)
    assert hen_agent.current_light_level != 50


@pytest.mark.asyncio
async def test_integration_feeding_flow_offline(monkeypatch):
    """
    End-to-end (offline):
    FeedControlAgent -> HenSimulator (feeding receive)
    """
    sent_feed = []
    sent_hen = []

    # --- Feed control agent + behaviour ---
    feed_agent = DummyAgent("feedcontrol@localhost")
    feed_agent.feed_state = FeedState(level=10, capacity=100)
    feed_agent.hunger_threshold = 60
    feed_agent.max_hens_per_batch = 1
    feed_agent.feed_cooldown_s = 0.0
    feed_agent.portion_size = 4
    feed_agent.low_feed_threshold = 0

    feed_agent.ui_jid = "ui@localhost"
    feed_agent.logger_jid = "logger@localhost"
    feed_agent.behavior_alarm_jid = "alarm@localhost"
    feed_agent.last_hunger = {"simulator1@localhost": 90}
    feed_agent.last_fed_at = {}

    feed_beh = FeedReceiveBehaviour()
    feed_beh.agent = feed_agent
    feed_beh.send = make_send_collector(sent_feed)

    monkeypatch.setattr(feed_behaviour_mod, "_now", lambda: 100.0)

    # --- Hen agent + feeding receive behaviour ---
    hen_agent = DummyAgent("simulator1@localhost")
    hen_agent.hen_id = "simulator1@localhost"
    hen_agent.state = HenState(hunger=90, aggression=0)

    hen_feed_recv = ReceiveFeedingBehaviour()
    hen_feed_recv.agent = hen_agent
    hen_feed_recv.send = make_send_collector(sent_hen)  # not used here

    # Act: feed control decides to feed
    await feed_beh.handle_batch_feeding()

    # It should send feed_dispensed message to hen
    hen_msgs = [m for m in sent_feed if m.get_metadata("conversation") == "feeding"]
    assert hen_msgs, "FeedControl should send feeding/feed_dispensed message to hen"
    msg_to_hen = hen_msgs[0]

    # Deliver to hen feeding receiver by mocking receive()
    async def fake_receive(timeout=1):
        return msg_to_hen

    hen_feed_recv.receive = fake_receive
    await hen_feed_recv.run()

    # Assert hunger decreased by portion
    assert hen_agent.state.hunger == 86
