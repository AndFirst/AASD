from pathlib import Path

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from repositories.event_repository import EventRepository
from utils.config_loader import load_config
from utils.messaging import parse_content


class LoggerAgent(Agent):
    class ReceiveBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            data = parse_content(msg)
            event_type = data.get("event_type") or msg.get_metadata("conversation") or "unknown"
            payload = data.get("payload", data)

            self.agent.repo.log(event_type, payload)
            print(f"[LOGGER] {event_type}: {payload}")

    async def setup(self):
        print("[LOGGER] Agent uruchomiony.")
        cfg = load_config()
        events_file = cfg["logging"]["events_file"]
        self.repo = EventRepository(events_file)
        self.add_behaviour(self.ReceiveBehaviour())


async def main():
    import asyncio
    from utils.config_loader import get_agent_credentials

    cfg = load_config()
    jid, password = get_agent_credentials("logger", cfg)
    agent = LoggerAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("LoggerAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję LoggerAgent...")
        await agent.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
