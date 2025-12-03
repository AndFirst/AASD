from agents.base_agent import BaseAgent


class StorageAgent(BaseAgent):
    """Agent odpowiedzialny za magazyn paszy."""

    async def setup(self):
        await super().setup()
        print(f"[STORAGE] {self.jid} feed storage initialized 🏠")
