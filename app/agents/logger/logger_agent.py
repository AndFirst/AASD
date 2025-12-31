from spade.agent import Agent

from agents.logger.logger_agent_behaviour import ReceiveBehaviour
from repositories.event_repository import EventRepository
from utils.config_loader import load_config


class LoggerAgent(Agent):
    def __init__(
        self, jid: str, password: str, port: int = 5222, verify_security: bool = False
    ):
        super().__init__(jid, password, port, verify_security)
        self.repo: EventRepository | None = None

    async def setup(self):
        print("[LOGGER] Agent uruchomiony.")
        cfg = load_config()

        events_file = cfg["logging"]["events_file"]
        self.repo = EventRepository(events_file)

        self.add_behaviour(ReceiveBehaviour())
