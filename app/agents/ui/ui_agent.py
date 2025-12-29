from spade.agent import Agent

from agents.ui.ui_agent_behaviour import ReceiveBehaviour


class UIAgent(Agent):
    async def setup(self):
        print("[UI] Agent uruchomiony.")
        self.add_behaviour(ReceiveBehaviour())


async def main():
    import asyncio
    from utils.config_loader import load_config, get_agent_credentials

    cfg = load_config()
    jid, password = get_agent_credentials("ui", cfg)

    agent = UIAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("UIAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję UIAgent...")
        await agent.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
