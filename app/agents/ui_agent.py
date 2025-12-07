from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content


class UIAgent(Agent):
    class ReceiveBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            data = parse_content(msg)
            sender = str(msg.sender)
            print(f"[UI] Aktualizacja od {sender}: {data}")

    async def setup(self):
        print("[UI] Agent uruchomiony.")
        self.add_behaviour(self.ReceiveBehaviour())


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
