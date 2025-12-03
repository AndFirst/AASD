from agents.base_agent import BaseAgent


class FeederAgent(BaseAgent):
    """Agent odpowiedzialny za podawanie paszy."""

    async def setup(self):
        await super().setup()
        print(f"[FEEDER] {self.jid} feeding system ready 🌾")
