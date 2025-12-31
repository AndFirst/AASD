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

        # 1) content
        data = parse_content(msg)

        # 2) metadane XMPP
        meta = msg.metadata or {}
        sender = str(getattr(msg, "sender", "") or "")
        conversation = meta.get("conversation") or "unknown"
        performative = meta.get("performative") or "inform"

        # 3) repo safety
        if not getattr(self.agent, "repo", None):
            # jakby coś było nie tak z init, nie crashuj agenta
            print("[LOGGER] WARNING: repo is None - pomijam zapis.")
            return

        event_type, payload, source = self._normalize_event(data, conversation, sender)

        log_record = {
            "timestamp": _utc_now_iso(),
            "sender": sender,
            "source": source,                 # ważne: często wysyłasz source=jID agenta
            "conversation": conversation,
            "performative": performative,
            "data": payload,
        }

        self.agent.repo.log(event_type, log_record)
        print(f"[LOGGER] {event_type}: {log_record}")

    def _normalize_event(self, data: Any, conversation: str, sender: str) -> tuple[str, dict, str | None]:
        """
        Normalizacja do jednego formatu:
        - event_type: string (kategoria eventu)
        - payload: dict (dane eventu)
        - source: opcjonalne pole 'source' z message content (jak istnieje)
        """

        event_type: str | None = None
        payload: Any = None
        source: str | None = None

        # --- preferowany format (u Ciebie to standard): ---
        # {
        #   "type": "log_event",
        #   "source": "...",
        #   "payload": { "event": "...", ... }
        # }
        if isinstance(data, dict):
            source = data.get("source") or None

            if data.get("type") == "log_event":
                payload = data.get("payload", {}) or {}
                if isinstance(payload, dict):
                    event_type = payload.get("event") or "log_event"
                else:
                    # payload nie jest dict -> opakuj
                    event_type = "log_event"
                    payload = {"payload": payload}

        # --- wsteczna kompatybilność (stary format): ---
        # { "event_type": "...", "payload": {...} }
        # UWAGA: tylko jeśli nie rozpoznaliśmy już nowego formatu
        if event_type is None:
            if isinstance(data, dict):
                event_type = data.get("event_type") or data.get("type")  # czasem type bywa eventem w starych agentach
                payload = data.get("payload", data)
                if source is None:
                    source = data.get("source") or None
            else:
                # data np. string/list itd.
                payload = {"payload": data}

        # --- final fallbacki ---
        if not event_type:
            # jeśli nadal brak, to conversation jako etykieta
            event_type = conversation or "unknown"

        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            payload = {"payload": payload}

        # jeśli source dalej brak, spróbuj użyć sender (nie zawsze to to samo, ale lepsze niż None)
        if source is None:
            source = sender or None

        return event_type, payload, source
