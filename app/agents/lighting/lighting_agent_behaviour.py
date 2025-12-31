import time

from spade.behaviour import CyclicBehaviour

from utils.config_loader import load_config
from utils.messaging import parse_content, build_message


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


class LightningBehaviour(CyclicBehaviour):
    async def on_start(self):
        cfg = load_config()
        n = int(
            (cfg.get("hen_simulator", {}) or {}).get(
                "count", getattr(self.agent, "hen_count", 5)
            )
        )
        if not hasattr(self.agent, "hen_light_levels") or not isinstance(
            self.agent.hen_light_levels, dict
        ):
            self.agent.hen_light_levels = {}

        for i in range(1, n + 1):
            hen_id = f"simulator{i}@localhost"
            if hen_id not in self.agent.hen_light_levels:
                self.agent.hen_light_levels[hen_id] = int(
                    getattr(self.agent, "neutral_level", 50)
                )

            await self._broadcast_light_update(reason="init", hen_id=hen_id)

    async def run(self):
        msg = await self.receive(timeout=10)
        if not msg:
            return

        if msg.get_metadata("conversation") != "lighting":
            return

        content = parse_content(msg) or {}
        msg_type = content.get("type")
        payload = content.get("payload", {}) or content

        if msg_type in {"set_light", "set_light_level"}:
            await self._handle_manual_set(payload)
            return

        if msg_type in {"aggression_update", "regulate_from_aggression"}:
            await self._handle_aggression_update(payload)
            return

    def _compute_target_level(self, aggression: int) -> int:
        neutral = int(getattr(self.agent, "neutral_level", 50))
        lo = int(getattr(self.agent, "min_level", 0))
        hi = int(getattr(self.agent, "max_level", 100))

        tmin = int(getattr(self.agent, "target_aggr_min", -3))
        tmax = int(getattr(self.agent, "target_aggr_max", 3))

        if tmin <= aggression <= tmax:
            return _clamp(neutral, lo, hi)

        gain = float(getattr(self.agent, "gain_per_aggression", 4.0))
        target = int(round(neutral + gain * aggression))
        return _clamp(target, lo, hi)

    def _allow_send(self, hen_id: str, new_level: int) -> bool:
        if not hen_id:
            return False

        now = time.monotonic()
        last_t = float(getattr(self.agent, "_last_set_at", {}).get(hen_id, 0.0))
        min_int = float(getattr(self.agent, "min_update_interval_s", 1.0))
        if now - last_t < min_int:
            return False

        cur = int(
            (getattr(self.agent, "hen_light_levels", {}) or {}).get(
                hen_id, getattr(self.agent, "neutral_level", 50)
            )
        )
        min_delta = int(getattr(self.agent, "min_delta_to_send", 2))
        if abs(int(new_level) - cur) < min_delta:
            return False

        return True

    async def _set_level_for_hen(self, hen_id: str, new_level: int, reason: str):
        lo = int(getattr(self.agent, "min_level", 0))
        hi = int(getattr(self.agent, "max_level", 100))

        new_level = _clamp(int(new_level), lo, hi)

        if not self._allow_send(hen_id, new_level):
            return

        self.agent.hen_light_levels[hen_id] = new_level

        if not hasattr(self.agent, "_last_set_at") or not isinstance(
            self.agent._last_set_at, dict
        ):
            self.agent._last_set_at = {}
        if not hasattr(self.agent, "_last_sent_level") or not isinstance(
            self.agent._last_sent_level, dict
        ):
            self.agent._last_sent_level = {}

        self.agent._last_set_at[hen_id] = time.monotonic()
        await self._broadcast_light_update(reason=reason, hen_id=hen_id)

    async def _handle_manual_set(self, payload: dict):
        hen_id = payload.get("hen_id")
        if not hen_id:
            return

        try:
            level = int(
                payload.get(
                    "level",
                    self.agent.hen_light_levels.get(hen_id, self.agent.neutral_level),
                )
            )
        except Exception:
            return

        reason = payload.get("reason", "manual_set")
        await self._set_level_for_hen(hen_id=hen_id, new_level=level, reason=reason)

    async def _handle_aggression_update(self, payload: dict):
        hen_id = payload.get("hen_id")
        if not hen_id:
            return

        try:
            aggression = int(payload.get("aggression", 0))
        except Exception:
            aggression = 0

        target = self._compute_target_level(aggression)

        cur = int(self.agent.hen_light_levels.get(hen_id, self.agent.neutral_level))
        print(
            f"[LIGHT] SETPOINT hen={hen_id} aggr={aggression} cur={cur} -> target={target}"
        )

        await self._set_level_for_hen(
            hen_id=hen_id, new_level=target, reason="regulate_to_target"
        )

    async def _broadcast_light_update(self, reason: str, hen_id: str):
        if not hen_id:
            return

        level = int(
            self.agent.hen_light_levels.get(
                hen_id, getattr(self.agent, "neutral_level", 50)
            )
        )

        msg_ui = build_message(
            to=self.agent.ui_jid,
            performative="inform",
            conversation="update_state",
            content={
                "type": "light_state_update",
                "source": str(self.agent.jid),
                "payload": {"level": level, "reason": reason, "hen_id": hen_id},
            },
        )
        await self.send(msg_ui)

        msg_log = build_message(
            to=self.agent.logger_jid,
            performative="inform",
            conversation="logging",
            content={
                "type": "log_event",
                "source": str(self.agent.jid),
                "payload": {
                    "event": "light_change",
                    "level": level,
                    "reason": reason,
                    "hen_id": hen_id,
                },
            },
        )
        await self.send(msg_log)

        msg_hen = build_message(
            to=hen_id,
            performative="inform",
            conversation="lighting",
            content={
                "type": "light_level_update",
                "source": str(self.agent.jid),
                "payload": {"level": level, "reason": reason, "hen_id": hen_id},
            },
        )
        await self.send(msg_hen)

        if not hasattr(self.agent, "_last_sent_level") or not isinstance(
            self.agent._last_sent_level, dict
        ):
            self.agent._last_sent_level = {}
        self.agent._last_sent_level[hen_id] = level
