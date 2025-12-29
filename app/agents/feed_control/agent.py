import asyncio

from spade.agent import Agent

from agents.feed_control.behaviour import ReceiveBehaviour
from models.environment_state import FeedState
from utils.config_loader import load_config, get_agent_credentials


class FeedControlAgent(Agent):
    def __init__(
            self, jid: str, password: str, port: int = 5222, verify_security: bool = False
    ):
        super().__init__(jid, password, port, verify_security)
        self.behavior_alarm_jid = None
        self.ui_jid = None
        self.logger_jid = None
        self.low_feed_threshold = None
        self.hunger_threshold = None
        self.portion_size = None
        self.feed_state = None

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

        self.add_behaviour(ReceiveBehaviour())


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
