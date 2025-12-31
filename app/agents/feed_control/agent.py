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

        self.behavior_alarm_jid: str | None = None
        self.ui_jid: str | None = None
        self.logger_jid: str | None = None

        self.low_feed_threshold: int = 0
        self.hunger_threshold: int = 0
        self.portion_size: int = 0

        self.feed_state: FeedState | None = None

        self.last_fed_at: dict[str, float] = {}
        self.feed_cooldown_s: float = 8.0

        self.max_hens_per_batch: int = 3

        self.last_hunger: dict[str, int] = {}

    async def setup(self):
        print("[FEED] Agent uruchomiony.")
        cfg = load_config()
        feeding_cfg = cfg.get("feeding", {}) or {}

        self.feed_cooldown_s = float(feeding_cfg.get("feed_cooldown_s", 8))
        self.max_hens_per_batch = int(feeding_cfg.get("max_hens_per_batch", 3))

        self.feed_state = FeedState(
            level=int(feeding_cfg.get("initial_feed_level", 0)),
            capacity=int(feeding_cfg.get("silo_capacity", 0)),
        )

        self.portion_size = int(feeding_cfg.get("portion_size", 1))
        self.hunger_threshold = int(feeding_cfg.get("hunger_threshold", 70))
        self.low_feed_threshold = int(feeding_cfg.get("low_feed_threshold", 10))

        self.logger_jid = cfg["agents"]["logger"]["jid"]
        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.behavior_alarm_jid = cfg["agents"]["behavior_alarm"]["jid"]

        self.add_behaviour(ReceiveBehaviour())


async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("feed_control", cfg)

    agent = FeedControlAgent(
        jid, password, verify_security=cfg["xmpp"]["verify_security"]
    )
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
