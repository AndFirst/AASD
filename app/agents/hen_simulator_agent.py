import asyncio
import random

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour

from models.hen_state import HenState
from utils.config_loader import load_config, get_agent_credentials
from utils.messaging import build_message


class HenSimulatorAgent(Agent):
    class SimulateBehaviour(PeriodicBehaviour):
        async def run(self):
            # Prosta symulacja – losowe wartości jak w Twojej wersji
            hunger = random.randint(0, 100)
            aggression = random.randint(0, 10)
            self.agent.state.hunger = hunger
            self.agent.state.aggression = aggression

            print(f"[SIM] Hunger={hunger}, Aggr={aggression}")

            # inform → FeedControlAgent (karmienie kur – FIPA inform)
            msg_feed = build_message(
                to=self.agent.feed_control_jid,
                performative="inform",
                conversation="feeding",
                content={
                    "type": "hunger_update",
                    "hunger": hunger,
                },
            )
            await self.send(msg_feed)

            # inform → BehaviorAndAlarmAgent (stan zachowania)
            msg_behavior = build_message(
                to=self.agent.behavior_alarm_jid,
                performative="inform",
                conversation="behavior",
                content={
                    "type": "behavior_update",
                    "hunger": hunger,
                    "aggression": aggression,
                },
            )
            await self.send(msg_behavior)

            # inform → UIAgent (aktualizacja stanu)
            msg_ui = build_message(
                to=self.agent.ui_jid,
                performative="inform",
                conversation="ui_update",
                content={
                    "event_type": "hen_state",
                    "payload": {
                        "hunger": hunger,
                        "aggression": aggression,
                    },
                },
            )
            await self.send(msg_ui)

    async def setup(self):
        print("[SIM] Agent uruchomiony.")
        self.state = HenState()

        cfg = load_config()
        self.feed_control_jid = cfg["agents"]["feed_control"]["jid"]
        self.behavior_alarm_jid = cfg["agents"]["behavior_alarm"]["jid"]
        self.ui_jid = cfg["agents"]["ui"]["jid"]

        # co 5 sekund wysyłamy stan
        self.add_behaviour(self.SimulateBehaviour(period=5))


async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("hen_simulator", cfg)

    agent = HenSimulatorAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("HenSimulatorAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję HenSimulatorAgent...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
