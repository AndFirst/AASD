import asyncio

from spade.agent import Agent

from agents.behavior_and_alarm.behavior_and_alarm_agent_behaviour import ReceiveBehaviour
from utils.config_loader import load_config, get_agent_credentials


class BehaviorAndAlarmAgent(Agent):
    def __init__(
            self, jid: str, password: str, port: int = 5222, verify_security: bool = False
    ):
        super().__init__(jid, password, port, verify_security)
        self.aggression_threshold = None
        self.ui_jid = None
        self.logger_jid = None
        self.lighting_jid = None
        

    async def setup(self):
        print("[BEHAV] Agent uruchomiony.")
        cfg = load_config()
        self.aggression_threshold = cfg["behavior"]["aggression_threshold"]

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
