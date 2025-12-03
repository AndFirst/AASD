from agents.base_agent import BaseAgent


class ChickenAgent(BaseAgent):
    """Agent reprezentujący pojedynczego kurczaka."""

    async def setup(self):
        await super().setup()
        print(f"[CHICKEN] {self.jid} is pecking around 🐔")
        # tutaj dodasz np. zachowania (behaviours)
