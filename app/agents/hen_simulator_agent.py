from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
import random
import asyncio


class HenSimulatorAgent(Agent):
    class SimulateBehaviour(PeriodicBehaviour):
        async def run(self):
            hunger = random.randint(0, 100)
            aggression = random.randint(0, 10)

            print(f"[SIM] Hunger={hunger}, Aggr={aggression}")

            msg = Message(to="feedcontrol@localhost")
            msg.set_metadata("performative", "inform")
            msg.body = f"hunger:{hunger};aggr:{aggression}"
            await self.send(msg)

    async def setup(self):
        print("[SIM] Agent uruchomiony.")
        # co 5 sekund wysyłamy stan
        self.add_behaviour(self.SimulateBehaviour(period=5))


async def main():
    agent = HenSimulatorAgent("simulator@localhost", "password")
    await agent.start()
    print("HenSimulatorAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję agenta...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
