import asyncio

from spade.agent import Agent

from agents.lighting.lighting_agent_behaviour import ControlBehaviour
from models.environment_state import LightingState
from utils.config_loader import load_config, get_agent_credentials


class LightingAgent(Agent):


    def __init__(
            self, jid: str, password: str, port: int = 5222, verify_security: bool = False
    ):
        super().__init__(jid, password, port, verify_security)
        self.logger_jid = None
        self.ui_jid = None
        self.light_state = None
        self.calm_level = None
        self.normal_level = None

    async def setup(self):
        print("[LIGHT] Agent uruchomiony.")
        cfg = load_config()
        light_cfg = cfg["lighting"]

        self.normal_level = light_cfg["normal_level"]
        self.calm_level = light_cfg["calm_level"]
        self.light_state = LightingState(level=self.normal_level, mode="normal")

        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.logger_jid = cfg["agents"]["logger"]["jid"]

        self.add_behaviour(ControlBehaviour())


async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("lighting", cfg)

    agent = LightingAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("LightingAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję LightingAgent...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
