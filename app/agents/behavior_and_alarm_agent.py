import asyncio

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from utils.config_loader import load_config, get_agent_credentials
from utils.messaging import build_message, parse_content


class BehaviorAndAlarmAgent(Agent):
    class ReceiveBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            content = parse_content(msg)
            conv = msg.get_metadata("conversation")

            if conv == "behavior" and content.get("type") == "behavior_update":
                await self.handle_behavior_update(content)
            elif conv == "alerts":
                await self.handle_external_alert(content)

        async def handle_behavior_update(self, content: dict):
            aggression = content.get("aggression", 0)
            hunger = content.get("hunger", 0)

            if aggression >= self.agent.aggression_threshold:
                print(f"[BEHAV] Wykryta agresja={aggression}, hunger={hunger}")
                await self.raise_critical_event(
                    "aggression_alert",
                    {"aggression": aggression, "hunger": hunger},
                )
                # próbujemy uspokoić kury przez zmianę światła
                await self.request_calm_lighting()

        async def handle_external_alert(self, content: dict):
            # np. brak paszy / niski poziom paszy
            event_type = content.get("event_type", "external_alert")
            payload = content.get("payload", {})
            print(f"[ALARM] Alert z innego agenta: {event_type}, {payload}")
            await self.raise_critical_event(event_type, payload)

        async def raise_critical_event(self, event_type: str, payload: dict):
            data = {
                "event_type": event_type,
                "payload": payload,
            }

            # inform → UIAgent
            msg_ui = build_message(
                to=self.agent.ui_jid,
                performative="inform",
                conversation="ui_update",
                content=data,
            )
            await self.send(msg_ui)

            # inform → LoggerAgent
            msg_log = build_message(
                to=self.agent.logger_jid,
                performative="inform",
                conversation="log",
                content=data,
            )
            await self.send(msg_log)

        async def request_calm_lighting(self):
            msg = build_message(
                to=self.agent.lighting_jid,
                performative="request",
                conversation="lighting",
                content={"type": "calm_hens"},
            )
            await self.send(msg)

    async def setup(self):
        print("[BEHAV] Agent uruchomiony.")
        cfg = load_config()
        self.aggression_threshold = cfg["behavior"]["aggression_threshold"]

        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.logger_jid = cfg["agents"]["logger"]["jid"]
        self.lighting_jid = cfg["agents"]["lighting"]["jid"]

        self.add_behaviour(self.ReceiveBehaviour())



async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("behavior_alarm", cfg)

    agent = BehaviorAndAlarmAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("BehaviorAndAlarmAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję BehaviorAndAlarmAgent...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
