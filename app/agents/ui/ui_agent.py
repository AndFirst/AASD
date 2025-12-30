from spade.agent import Agent

from agents.ui.ui_agent_behaviour import ReceiveBehaviour


class UIAgent(Agent):
    async def setup(self):
        print("[UI] Agent uruchomiony.")

        # Stan widoku (agregacja)
        self.hens: dict[str, dict] = {}
        self.feed: dict = {}
        self.lights_by_hen: dict[str, dict] = {}
        self.last_events: list[dict] = []

        # Uwaga: clear_screen domyślnie False (mniej migania)
        self.add_behaviour(ReceiveBehaviour(clear_screen=False))
