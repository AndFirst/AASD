import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_monotonic() -> float:
    return time.monotonic()


def _clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def _stable_hash(obj) -> str:
    try:
        if obj is None:
            return "none"
        if isinstance(obj, (str, int, float, bool)):
            return str(obj)
        if isinstance(obj, dict):
            items = sorted((str(k), _stable_hash(v)) for k, v in obj.items())
            return "{" + ",".join(f"{k}:{v}" for k, v in items) + "}"
        if isinstance(obj, list):
            return "[" + ",".join(_stable_hash(x) for x in obj) + "]"
        return str(obj)
    except Exception:
        return "err"


class ReceiveBehaviour(CyclicBehaviour):
    _WS_EVENT_BLOCKLIST = {
        "hen_state_update",
        "light_state_update",
        "feed_state_update",
        "feed_dispensed",
    }

    def __init__(
        self,
        *,
        ws_hub=None,
        render_interval_sec: float = 1.0,
        clear_screen: bool = False,
        also_print_console: bool = False,
        dedup_window_sec: float = 0.0,
    ):
        super().__init__()
        self.ws_hub = ws_hub
        self.render_interval_sec = float(render_interval_sec)
        self._last_render_at = 0.0
        self._dirty = False

        self.clear_screen = bool(clear_screen)
        self.also_print_console = bool(also_print_console)

        self._dedup_window_sec = float(dedup_window_sec)
        self._dedup: dict[str, float] = {}

    async def run(self):
        if not hasattr(self.agent, "hens"):
            self.agent.hens = {}
        if not hasattr(self.agent, "feed"):
            self.agent.feed = {}
        if not hasattr(self.agent, "light"):
            self.agent.light = {}
        if not hasattr(self.agent, "lights_by_hen"):
            self.agent.lights_by_hen = {}

        first = await self.receive(timeout=1)
        if not first:
            await self._maybe_render_snapshot()
            return

        msgs = [first]
        while True:
            m = await self.receive(timeout=0)
            if not m:
                break
            msgs.append(m)

        any_state_changed = False

        for msg in msgs:
            data = parse_content(msg) or {}
            sender = str(getattr(msg, "sender", "") or "")
            conv = msg.get_metadata("conversation") or "unknown"

            changed = False
            if conv == "update_state":
                changed = await self.handle_update_state(sender, data)
            elif conv == "ui_update":
                changed = await self.handle_legacy_ui_update(sender, data)
            elif conv == "logging":
                changed = await self.handle_logging(sender, data)
            else:
                await self._emit_event(
                    sender=sender,
                    event_type=f"conv:{conv}",
                    payload=data,
                    dedup_key=f"conv:{conv}:{sender}:{_stable_hash(data)}",
                )

            if changed:
                any_state_changed = True

        if any_state_changed:
            self._dirty = True
            await self._maybe_render_snapshot()

    async def _emit_event(
        self,
        *,
        sender: str,
        event_type: str,
        payload: dict | Any,
        dedup_key: Optional[str] = None,
        ts: Optional[str] = None,
    ) -> None:
        if not self.ws_hub:
            return

        if dedup_key and self._dedup_window_sec > 0:
            now = _now_monotonic()
            last = self._dedup.get(dedup_key)
            if last is not None and (now - last) < self._dedup_window_sec:
                return
            self._dedup[dedup_key] = now

        event = {
            "ts": ts or _utc_now_iso(),
            "sender": sender,
            "type": event_type,
            "payload": payload,
        }

        try:
            await self.ws_hub.broadcast(
                {
                    "type": "ui_event",
                    "ts": _utc_now_iso(),
                    "event": event,
                }
            )
        except Exception:
            return

    def _make_snapshot(self) -> Dict[str, Any]:
        return {
            "type": "ui_snapshot",
            "ts": _utc_now_iso(),
            "state": {
                "feed": self.agent.feed or {},
                "light": self.agent.light or {},
                "lights_by_hen": getattr(self.agent, "lights_by_hen", {}) or {},
                "hens": self.agent.hens or {},
            },
        }

    async def _broadcast_snapshot(self) -> None:
        if not self.ws_hub:
            return
        try:
            await self.ws_hub.broadcast(self._make_snapshot())
        except Exception:
            return

    async def _maybe_render_snapshot(self):
        if not self._dirty:
            return
        now = _now_monotonic()
        if now - self._last_render_at < self.render_interval_sec:
            return

        self._last_render_at = now
        self._dirty = False

        await self._broadcast_snapshot()

        if self.also_print_console:
            self.render()

    async def handle_logging(self, sender: str, data: dict) -> bool:
        if not isinstance(data, dict):
            return False

        payload = data.get("data") or {}
        if not isinstance(payload, dict):
            payload = {"payload": payload}

        event = payload.get("event")
        ts = data.get("timestamp") or _utc_now_iso()

        await self._emit_event(
            sender=sender,
            event_type=f"log:{event or 'unknown'}",
            payload=payload or data,
            dedup_key=(
                f"log:{event}:{payload.get('hen_id')}:{payload.get('level')}:"
                f"{payload.get('reason')}:{payload.get('aggression')}:{payload.get('hunger')}"
            ),
            ts=ts,
        )

        if event == "feed_dispensed":
            return await self.handle_update_state(
                sender, {"type": "feed_dispensed", "payload": payload}
            )
        if event == "light_change":
            return await self.handle_update_state(
                sender, {"type": "light_state_update", "payload": payload}
            )
        if event in ("aggression_alert", "critical_event"):
            return await self.handle_update_state(
                sender, {"type": "critical_event", "payload": payload}
            )

        return False

    async def handle_update_state(self, sender: str, data: dict) -> bool:
        if not isinstance(data, dict):
            return False

        msg_type = data.get("type")
        payload = data.get("payload", {}) or {}

        changed = False

        if msg_type == "hen_state_update":
            hen_id = payload.get("hen_id") or data.get("source") or sender
            new_state = {
                "hunger": int(payload.get("hunger", 0) or 0),
                "aggression": int(payload.get("aggression", 0) or 0),
                "last_update": _utc_now_iso(),
            }
            old = self.agent.hens.get(hen_id)
            self.agent.hens[hen_id] = new_state
            changed = old != new_state

        elif msg_type == "feed_state_update":
            new_feed = {
                **(self.agent.feed or {}),
                "capacity": payload.get("capacity"),
                "remaining_feed": payload.get("remaining_feed"),
                "last_action": "state_update",
                "last_update": _utc_now_iso(),
            }
            changed = new_feed != (self.agent.feed or {})
            self.agent.feed = new_feed

        elif msg_type == "feed_dispensed":
            new_feed = {
                **(self.agent.feed or {}),
                "capacity": payload.get("capacity"),
                "remaining_feed": payload.get("remaining_feed"),
                "last_action": "feed_dispensed",
                "last_update": _utc_now_iso(),
                "hen_id": payload.get("hen_id"),
                "portion": payload.get("portion"),
                "hunger_before": payload.get("hunger_before"),
            }
            feed_changed = new_feed != (self.agent.feed or {})
            self.agent.feed = new_feed
            changed = feed_changed

        elif msg_type == "light_state_update":
            level = payload.get("level")
            hen_id = payload.get("hen_id")
            entry = {
                "level": level,
                "reason": payload.get("reason"),
                "hen_id": hen_id,
                "last_update": _utc_now_iso(),
            }

            if not hen_id:
                old = self.agent.light if isinstance(self.agent.light, dict) else {}
                self.agent.light = entry
                changed = old != entry
            else:
                if (
                    not hasattr(self.agent, "lights_by_hen")
                    or self.agent.lights_by_hen is None
                ):
                    self.agent.lights_by_hen = {}
                old = self.agent.lights_by_hen.get(hen_id)
                self.agent.lights_by_hen[hen_id] = entry
                changed = old != entry

        elif msg_type == "critical_event":
            changed = False

        if (msg_type or "") not in self._WS_EVENT_BLOCKLIST:
            await self._emit_event(
                sender=sender,
                event_type=msg_type or "unknown_update",
                payload=payload or data,
                dedup_key=f"update:{msg_type}:{sender}:{_stable_hash(payload or data)}",
            )

        return changed

    async def handle_legacy_ui_update(self, sender: str, data: dict) -> bool:
        if not isinstance(data, dict):
            return False

        event_type = data.get("event_type") or "legacy_event"
        payload = data.get("payload", {}) or {}

        changed = False

        if event_type == "hen_state":
            hen_id = sender
            new_state = {
                "hunger": int(payload.get("hunger", 0) or 0),
                "aggression": int(payload.get("aggression", 0) or 0),
                "last_update": _utc_now_iso(),
            }
            old = self.agent.hens.get(hen_id)
            self.agent.hens[hen_id] = new_state
            changed = old != new_state

        elif event_type == "feed_dispensed":
            new_feed = {
                **(self.agent.feed or {}),
                "capacity": payload.get("capacity"),
                "remaining_feed": payload.get("remaining_feed"),
                "last_action": "feed_dispensed",
                "last_update": _utc_now_iso(),
                "portion": payload.get("portion"),
                "hunger_before": payload.get("hunger_before"),
            }
            changed = new_feed != (self.agent.feed or {})
            self.agent.feed = new_feed

        elif event_type == "light_change":
            new_light = {
                "level": payload.get("level"),
                "hen_id": payload.get("hen_id"),
                "reason": payload.get("reason"),
                "last_update": _utc_now_iso(),
            }
            old = self.agent.light if isinstance(self.agent.light, dict) else {}
            self.agent.light = new_light
            changed = old != new_light

        await self._emit_event(
            sender=sender,
            event_type=f"legacy:{event_type}",
            payload=payload or data,
            dedup_key=f"legacy:{event_type}:{sender}:{_stable_hash(payload or data)}",
        )

        return changed

    def render(self):
        if self.clear_screen:
            _clear_console()

        print("\n" + "=" * 70)
        print(f"[UI] Stan kurnika | {_utc_now_iso()}")
        print("=" * 70)

        if self.agent.feed:
            print(
                f"Pasza: remaining={self.agent.feed.get('remaining_feed')} capacity={self.agent.feed.get('capacity')} | "
                f"last_action={self.agent.feed.get('last_action')} | "
                f"hen={self.agent.feed.get('hen_id')} | portion={self.agent.feed.get('portion')}"
            )
        else:
            print("Pasza: brak danych")

        if getattr(self.agent, "lights_by_hen", None):
            print("Światło per kura:")
            for hid, lst in sorted(self.agent.lights_by_hen.items()):
                print(
                    f"  • {hid:<22} level={lst.get('level')} | "
                    f"reason={lst.get('reason')} | last={lst.get('last_update')}"
                )
        else:
            print("Światło: brak danych")

        print("-" * 70)

        print(f"Kury: {len(self.agent.hens)}")
        for hen_id, st in self.agent.hens.items():
            st = st or {}
            hunger = int(st.get("hunger", 0) or 0)
            aggr = int(st.get("aggression", 0) or 0)
            last = st.get("last_update")
            print(f"  • {hen_id:<22} hunger={hunger:>3} | aggr={aggr:>3} | last={last}")

        print("=" * 70)
