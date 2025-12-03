from agents.base_agent import BaseAgent


class ManagerAgent(BaseAgent):
    """Agent zarządzający całym systemem karmienia."""

    async def setup(self):
        await super().setup()
        print(f"[MANAGER] {self.jid} controlling agents ⚙️")
