import time

from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content, build_message


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


class ReceiveBehaviour(CyclicBehaviour):
    def __init__(self):
        super().__init__()
        self._last_regulate_at: dict[str, float] = {}
        self._last_sent_aggr: dict[str, int] = {}

    async def run(self):
        msg = await self.receive(timeout=10)
        if not msg:
            return

        content = parse_content(msg) or {}
        conv = msg.get_metadata("conversation")
        msg_type = content.get("type")

        if conv == "behavior" and msg_type == "behavior_update":
            await self.handle_behavior_message(content)

        elif conv == "behavior" and msg_type == "aggression_detected":
            await self.handle_behavior_message(content)

        elif conv == "alerts":
            await self.handle_external_alert(content)

    async def handle_behavior_message(self, content: dict):
        hen_id = content.get("hen_id")
        if not hen_id:
            return

        aggression = int(content.get("aggression", 0) or 0)
        hunger = int(content.get("hunger", 0) or 0)
        aggression = _clamp(
            aggression, -self.agent.max_abs_aggression, self.agent.max_abs_aggression
        )

        if abs(aggression) >= int(self.agent.aggression_threshold):
            print(
                f"[BEHAV] ALARM: aggression={aggression}, hunger={hunger}, hen_id={hen_id}"
            )

            await self.raise_critical_event(
                event_type="aggression_alert",
                payload={
                    "hen_id": hen_id,
                    "aggression": aggression,
                    "hunger": hunger,
                    "threshold": self.agent.aggression_threshold,
                },
            )
        await self._maybe_send_aggression_update(
            hen_id=hen_id, aggression=aggression, hunger=hunger
        )

    async def _maybe_send_aggression_update(
        self, hen_id: str, aggression: int, hunger: int
    ):
        now = time.monotonic()
        last_t = float(self._last_regulate_at.get(hen_id, 0.0))

        if (now - last_t) < float(self.agent.regulate_min_interval_sec):
            return

        last_aggr = self._last_sent_aggr.get(hen_id)
        if last_aggr is not None and last_aggr == aggression:
            return

        self._last_regulate_at[hen_id] = now
        self._last_sent_aggr[hen_id] = aggression

        print(
            f"[BEHAV] AGGR->LIGHT: hen_id={hen_id}, aggr={aggression} "
            f"(target {self.agent.aggression_target_min}..{self.agent.aggression_target_max})"
        )

        await self.send_aggression_update_to_lighting(
            reason="aggression_update",
            hen_id=hen_id,
            aggression=aggression,
            hunger=hunger,
        )

    async def handle_external_alert(self, content: dict):
        event_type = (
            content.get("event_type") or content.get("type") or "external_alert"
        )
        payload = content.get("payload", {}) or {}

        print(f"[ALARM] Alert z innego agenta: {event_type}, {payload}")
        await self.raise_critical_event(event_type, payload)

    async def raise_critical_event(self, event_type: str, payload: dict):
        msg_ui = build_message(
            to=self.agent.ui_jid,
            performative="inform",
            conversation="update_state",
            content={
                "type": "critical_event",
                "source": str(self.agent.jid),
                "payload": {
                    "event": event_type,
                    **(payload or {}),
                },
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
                    "event": event_type,
                    **(payload or {}),
                },
            },
        )
        await self.send(msg_log)

    async def send_aggression_update_to_lighting(
        self, reason: str, hen_id: str, aggression: int, hunger: int
    ):
        msg = build_message(
            to=self.agent.lighting_jid,
            performative="request",
            conversation="lighting",
            content={
                "type": "aggression_update",
                "payload": {
                    "reason": reason,
                    "hen_id": hen_id,
                    "aggression": int(aggression),
                    "hunger": int(hunger),
                },
            },
        )
        await self.send(msg)
