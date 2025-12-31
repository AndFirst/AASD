from datetime import datetime, timezone
from typing import Any

from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReceiveBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=10)
        if not msg:
            return

        data = parse_content(msg)

        meta = msg.metadata or {}
        sender = str(getattr(msg, "sender", "") or "")
        conversation = meta.get("conversation") or "unknown"
        performative = meta.get("performative") or "inform"

        if not getattr(self.agent, "repo", None):
            print("[LOGGER] WARNING: repo is None - pomijam zapis.")
            return

        event_type, payload, source = self._normalize_event(data, conversation, sender)

        log_record = {
            "timestamp": _utc_now_iso(),
            "sender": sender,
            "source": source,
            "conversation": conversation,
            "performative": performative,
            "data": payload,
        }

        self.agent.repo.log(event_type, log_record)
        print(f"[LOGGER] {event_type}: {log_record}")

    def _normalize_event(
        self, data: Any, conversation: str, sender: str
    ) -> tuple[str, dict, str | None]:
        event_type: str | None = None
        payload: Any = None
        source: str | None = None

        if isinstance(data, dict):
            source = data.get("source") or None

            if data.get("type") == "log_event":
                payload = data.get("payload", {}) or {}
                if isinstance(payload, dict):
                    event_type = payload.get("event") or "log_event"
                else:
                    event_type = "log_event"
                    payload = {"payload": payload}

        if event_type is None:
            if isinstance(data, dict):
                event_type = data.get("event_type") or data.get("type")
                payload = data.get("payload", data)
                if source is None:
                    source = data.get("source") or None
            else:
                payload = {"payload": data}
        if not event_type:
            event_type = conversation or "unknown"

        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            payload = {"payload": payload}
        if source is None:
            source = sender or None

        return event_type, payload, source
