from spade.agent import Agent

from agents.logger.logger_agent_behaviour import ReceiveBehaviour
from repositories.event_repository import EventRepository
from utils.config_loader import load_config


class LoggerAgent(Agent):
    def __init__(
            self, jid: str, password: str, port: int = 5222, verify_security: bool = False
    ):
        super().__init__(jid, password, port, verify_security)
        self.repo = None

    async def setup(self):
        print("[LOGGER] Agent uruchomiony.")
        cfg = load_config()
        events_file = cfg["logging"]["events_file"]
        self.repo = EventRepository(events_file)
        self.add_behaviour(ReceiveBehaviour())


async def main():
    import asyncio
    from utils.config_loader import get_agent_credentials

    cfg = load_config()
    jid, password = get_agent_credentials("logger", cfg)
    agent = LoggerAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("LoggerAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję LoggerAgent...")
        await agent.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
