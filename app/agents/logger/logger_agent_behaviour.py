from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content


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
