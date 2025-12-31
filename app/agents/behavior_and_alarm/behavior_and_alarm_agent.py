import asyncio
from spade.agent import Agent

from agents.behavior_and_alarm.behavior_and_alarm_agent_behaviour import ReceiveBehaviour
from utils.config_loader import load_config, get_agent_credentials


class BehaviorAndAlarmAgent(Agent):
    def __init__(self, jid: str, password: str, port: int = 5222, verify_security: bool = False):
        super().__init__(jid, password, port, verify_security)

        # Aggression: -10..+10 (twardy clamp)
        self.max_abs_aggression: int = 10

        # “Idealnie”: aggression w [-3, +3]
        self.aggression_target_min: int = -3
        self.aggression_target_max: int = 3

        # Próg alarmu (np. 7) -> alarm dla |aggression| >= threshold
        self.aggression_threshold: int = 7

        # Anti-spam (per kura): min czas między kolejnymi requestami regulacji
        self.regulate_min_interval_sec: float = 2.0

        self.ui_jid: str | None = None
        self.logger_jid: str | None = None
        self.lighting_jid: str | None = None

    async def setup(self):
        print("[BEHAV] Agent uruchomiony.")
        cfg = load_config()

        beh = cfg.get("behavior", {}) or {}

        self.aggression_threshold = int(beh.get("aggression_threshold", self.aggression_threshold))
        self.aggression_target_min = int(beh.get("aggression_target_min", self.aggression_target_min))
        self.aggression_target_max = int(beh.get("aggression_target_max", self.aggression_target_max))
        self.regulate_min_interval_sec = float(beh.get("regulate_min_interval_sec", self.regulate_min_interval_sec))

        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.logger_jid = cfg["agents"]["logger"]["jid"]
        self.lighting_jid = cfg["agents"]["lighting"]["jid"]

        self.add_behaviour(ReceiveBehaviour())


async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("behavior_alarm", cfg)

    agent = BehaviorAndAlarmAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("BehaviorAndAlarmAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję BehaviorAndAlarmAgent...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
