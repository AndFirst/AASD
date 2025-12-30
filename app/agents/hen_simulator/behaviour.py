import random

from spade.behaviour import PeriodicBehaviour

from utils.messaging import build_message


class SimulateBehaviour(PeriodicBehaviour):
    async def run(self):
        hunger = random.randint(0, 100)
        aggression = random.randint(0, 10)
        self.agent.state.hunger = hunger
        self.agent.state.aggression = aggression

        print(f"[SIM] Hunger={hunger}, Aggr={aggression}")

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
