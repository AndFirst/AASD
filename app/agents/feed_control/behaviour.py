import time
from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content, build_message


def _now() -> float:
    return time.monotonic()


class ReceiveBehaviour(CyclicBehaviour):
    async def on_start(self):
        # stan początkowy paszy do UI + Logger (żeby UI nie miało "brak danych")
        await self._broadcast_feed_state_update(reason="init")

    async def run(self):
        msg = await self.receive(timeout=10)
        if not msg:
            return

        content = parse_content(msg) or {}
        conv = msg.get_metadata("conversation")
        msg_type = content.get("type")

        # Symulator -> FeedControl
        if conv == "feeding" and msg_type in ("hunger_update", "hunger_high"):
            try:
                hunger = int(content.get("hunger", 0) or 0)
            except Exception:
                hunger = 0

            hen_id = content.get("hen_id")
            if not hen_id:
                print("[FEED] Brak hen_id w wiadomości - ignoruję.")
                return

            # zapamiętaj ostatni hunger tej kury (do batch karmienia)
            self.agent.last_hunger[hen_id] = hunger

            print(f"[FEED] Otrzymano hunger={hunger} od hen_id={hen_id}")

            # Uruchom karmienie “batch” (kilka kur naraz), nie tylko tej jednej
            await self.handle_batch_feeding()

    async def handle_batch_feeding(self):
        """
        Karmi wiele kur naraz:
        - wybiera wszystkie kury z hunger >= hunger_threshold
        - respektuje cooldown per kura
        - karmi max max_hens_per_batch na raz
        - kończy jak skończy się pasza
        """
        if not self.agent.feed_state:
            return

        # brak paszy w ogóle
        if int(self.agent.feed_state.level) <= 0:
            # wyślij alert “no_feed” dla tych, które aktualnie przekraczają próg
            for hen_id, hunger in list(self.agent.last_hunger.items()):
                if int(hunger) >= int(self.agent.hunger_threshold):
                    await self.send_no_feed_alert(hen_id=hen_id, hunger=int(hunger))
            # i zaktualizuj UI/Logger stanem "0"
            await self._broadcast_feed_state_update(reason="no_feed")
            return

        # kandydaci: hunger >= próg
        candidates = [
            (hen_id, int(hunger))
            for hen_id, hunger in (self.agent.last_hunger or {}).items()
            if int(hunger) >= int(self.agent.hunger_threshold)
        ]
        if not candidates:
            return

        # sortuj: najpierw najbardziej głodne
        candidates.sort(key=lambda x: x[1], reverse=True)

        fed_any = False
        fed_count = 0

        for hen_id, hunger in candidates:
            if fed_count >= int(self.agent.max_hens_per_batch):
                break

            # jeśli skończy się pasza, przerwij
            if int(self.agent.feed_state.level) <= 0:
                await self.send_no_feed_alert(hen_id=hen_id, hunger=hunger)
                break

            # cooldown per kura
            now = _now()
            last = float(self.agent.last_fed_at.get(hen_id, 0.0))
            if now - last < float(self.agent.feed_cooldown_s):
                continue

            portion = min(int(self.agent.feed_state.level), int(self.agent.portion_size))
            if portion <= 0:
                await self.send_no_feed_alert(hen_id=hen_id, hunger=hunger)
                break

            # zjedz z silosu
            self.agent.feed_state.level -= portion
            self.agent.last_fed_at[hen_id] = now

            print(f"[FEED] Karmienie: hen_id={hen_id}, porcja={portion}, zapas={self.agent.feed_state.level}")

            # 1) symulator -> zmniejsza hunger
            await self.send_feed_dispensed_to_hen(hen_id=hen_id, amount=portion)

            # 2) Logger + UI (event)
            await self.notify_feed_dispensed(hen_id=hen_id, portion=portion, hunger_before=hunger)

            fed_any = True
            fed_count += 1

        # jeśli cokolwiek się zmieniło, wyślij zaktualizowany stan paszy
        if fed_any:
            await self._broadcast_feed_state_update(reason="batch_feed")

        # Niski poziom paszy
        if int(self.agent.feed_state.level) <= int(self.agent.low_feed_threshold):
            await self.send_low_feed_warning()

    async def _broadcast_feed_state_update(self, reason: str):
        """
        Prosty update stanu paszy (init + każda zmiana poziomu).
        UI: conversation=update_state, type=feed_state_update
        Logger: conversation=logging, type=log_event (event=feed_state_update)
        """
        if not self.agent.feed_state:
            return

        remaining = int(self.agent.feed_state.level)
        capacity = int(self.agent.feed_state.capacity)

        # UI
        msg_ui = build_message(
            to=self.agent.ui_jid,
            performative="inform",
            conversation="update_state",
            content={
                "type": "feed_state_update",
                "source": str(self.agent.jid),
                "payload": {
                    "remaining_feed": remaining,
                    "capacity": capacity,
                    "reason": reason,
                },
            },
        )
        await self.send(msg_ui)

        # Logger
        msg_log = build_message(
            to=self.agent.logger_jid,
            performative="inform",
            conversation="logging",
            content={
                "type": "log_event",
                "source": str(self.agent.jid),
                "payload": {
                    "event": "feed_state_update",
                    "remaining_feed": remaining,
                    "capacity": capacity,
                    "reason": reason,
                },
            },
        )
        await self.send(msg_log)

    async def send_feed_dispensed_to_hen(self, hen_id: str, amount: int):
        """
        inform(feed_dispensed) -> HenSimulatorAgent
        Symulator po tym zmniejsza hunger.
        """
        msg_hen = build_message(
            to=hen_id,
            performative="inform",
            conversation="feeding",
            content={
                "type": "feed_dispensed",
                "hen_id": hen_id,
                "amount": int(amount),
            },
        )
        await self.send(msg_hen)

    async def notify_feed_dispensed(self, hen_id: str, portion: int, hunger_before: int):
        # UI: update_state
        msg_ui = build_message(
            to=self.agent.ui_jid,
            performative="inform",
            conversation="update_state",
            content={
                "type": "feed_dispensed",
                "source": str(self.agent.jid),
                "payload": {
                    "hen_id": hen_id,
                    "portion": int(portion),
                    "remaining_feed": int(self.agent.feed_state.level),
                    "hunger_before": int(hunger_before),
                },
            },
        )
        await self.send(msg_ui)

        # Logger: logging
        msg_logger = build_message(
            to=self.agent.logger_jid,
            performative="inform",
            conversation="logging",
            content={
                "type": "log_event",
                "source": str(self.agent.jid),
                "payload": {
                    "event": "feed_dispensed",
                    "hen_id": hen_id,
                    "portion": int(portion),
                    "remaining_feed": int(self.agent.feed_state.level),
                    "hunger_before": int(hunger_before),
                },
            },
        )
        await self.send(msg_logger)

    async def send_low_feed_warning(self):
        payload = {
            "type": "low_feed_warning",
            "source": str(self.agent.jid),
            "payload": {
                "remaining_feed": int(self.agent.feed_state.level),
                "threshold": int(self.agent.low_feed_threshold),
            },
        }

        msg_alarm = build_message(
            to=self.agent.behavior_alarm_jid,
            performative="inform",
            conversation="alerts",
            content=payload,
        )
        await self.send(msg_alarm)

    async def send_no_feed_alert(self, hen_id: str, hunger: int):
        payload = {
            "type": "no_feed",
            "source": str(self.agent.jid),
            "payload": {
                "hen_id": hen_id,
                "hunger": int(hunger),
                "remaining_feed": int(self.agent.feed_state.level) if self.agent.feed_state else 0,
            },
        }

        msg_alarm = build_message(
            to=self.agent.behavior_alarm_jid,
            performative="inform",
            conversation="alerts",
            content=payload,
        )
        await self.send(msg_alarm)
