from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import asyncio


class FeedControlAgent(Agent):
    class ReceiveBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                print("[FEED] Otrzymano:", msg.body)

    async def setup(self):
        print("[FEED] Agent uruchomiony.")
        self.add_behaviour(self.ReceiveBehaviour())


async def main():
    agent = FeedControlAgent("feedcontrol@localhost", "password")  # JID + hasło z prosody
    await agent.start(auto_register=True)
    print("FeedControlAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję agenta...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
