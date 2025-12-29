import asyncio

from spade.agent import Agent

from agents.hen_simulator.behaviour import SimulateBehaviour
from models.hen_state import HenState
from utils.config_loader import load_config, get_agent_credentials


class HenSimulatorAgent(Agent):
    def __init__(
            self, jid: str,
            password: str,
            port: int = 5222,
            verify_security: bool = False
    ):
        super().__init__(jid, password, port, verify_security)
        self.state = None
        self.feed_control_jid = None
        self.behavior_alarm_jid = None
        self.ui_jid = None

    async def setup(self):
        print("[SIM] Agent uruchomiony.")
        self.state = HenState()

        cfg = load_config()
        self.feed_control_jid = cfg["agents"]["feed_control"]["jid"]
        self.behavior_alarm_jid = cfg["agents"]["behavior_alarm"]["jid"]
        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.add_behaviour(SimulateBehaviour(period=5))


async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("hen_simulator", cfg)

    agent = HenSimulatorAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("HenSimulatorAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję HenSimulatorAgent...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
