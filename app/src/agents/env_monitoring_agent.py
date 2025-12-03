from agents.base_agent import BaseAgent


class EnvMonitoringAgent(BaseAgent):
    """Agent monitorujący środowisko (np. temperatura, wilgotność)."""

    async def setup(self):
        await super().setup()
        print(f"[ENV] {self.jid} monitoring environment 🌡️")
