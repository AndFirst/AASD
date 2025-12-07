import asyncio

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from models.environment_state import FeedState
from utils.config_loader import load_config, get_agent_credentials
from utils.messaging import build_message, parse_content


class FeedControlAgent(Agent):
    class ReceiveBehaviour(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            content = parse_content(msg)
            msg_type = content.get("type")

            if msg.get_metadata("conversation") == "feeding" and msg_type == "hunger_update":
                hunger = content.get("hunger", 0)
                await self.handle_hunger(hunger)

        # --------------------------
        #  LOGIKA FEED CONTROL
        # --------------------------

        async def handle_hunger(self, hunger: int):
            print(f"[FEED] Otrzymano poziom głodu: {hunger}")

            if hunger < self.agent.hunger_threshold:
                return

            if self.agent.feed_state.level <= 0:
                await self.send_no_feed_alert(hunger)
                return

            portion = min(self.agent.feed_state.level, self.agent.portion_size)
            self.agent.feed_state.level -= portion
            print(f"[FEED] Karmienie kur, porcja={portion}, zapas={self.agent.feed_state.level}")

            await self.notify_feed_dispensed(portion, hunger)

            if self.agent.feed_state.level <= self.agent.low_feed_threshold:
                await self.send_low_feed_warning()

        async def notify_feed_dispensed(self, portion: int, hunger: int):
            payload = {
                "event_type": "feed_dispensed",
                "payload": {
                    "portion": portion,
                    "remaining_feed": self.agent.feed_state.level,
                    "hunger_before": hunger,
                },
            }

            # inform → LoggerAgent
            msg_logger = build_message(
                to=self.agent.logger_jid,
                performative="inform",
                conversation="feeding",
                content=payload,
            )
            await self.send(msg_logger)

            # inform → UIAgent
            msg_ui = build_message(
                to=self.agent.ui_jid,
                performative="inform",
                conversation="ui_update",
                content=payload,
            )
            await self.send(msg_ui)

        async def send_low_feed_warning(self):
            payload = {
                "event_type": "low_feed_warning",
                "payload": {
                    "remaining_feed": self.agent.feed_state.level,
                },
            }

            msg_alarm = build_message(
                to=self.agent.behavior_alarm_jid,
                performative="inform",
                conversation="alerts",
                content=payload,
            )
            await self.send(msg_alarm)

        async def send_no_feed_alert(self, hunger: int):
            payload = {
                "event_type": "no_feed",
                "payload": {
                    "hunger": hunger,
                    "remaining_feed": self.agent.feed_state.level,
                },
            }

            msg_alarm = build_message(
                to=self.agent.behavior_alarm_jid,
                performative="inform",
                conversation="alerts",
                content=payload,
            )
            await self.send(msg_alarm)

    # ------------------------
    # SETUP AGENTA
    # ------------------------
    async def setup(self):
        print("[FEED] Agent uruchomiony.")
        cfg = load_config()

        feeding_cfg = cfg["feeding"]
        self.feed_state = FeedState(
            level=feeding_cfg["initial_feed_level"],
            capacity=feeding_cfg["silo_capacity"],
        )
        self.portion_size = feeding_cfg["portion_size"]
        self.hunger_threshold = feeding_cfg["hunger_threshold"]
        self.low_feed_threshold = feeding_cfg["low_feed_threshold"]

        self.logger_jid = cfg["agents"]["logger"]["jid"]
        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.behavior_alarm_jid = cfg["agents"]["behavior_alarm"]["jid"]

        self.add_behaviour(self.ReceiveBehaviour())



async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("feed_control", cfg)

    agent = FeedControlAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("FeedControlAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję FeedControlAgent...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
