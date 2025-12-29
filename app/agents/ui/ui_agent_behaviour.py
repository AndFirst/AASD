from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content


class ReceiveBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=10)
        if not msg:
            return

        data = parse_content(msg)
        sender = str(msg.sender)
        print(f"[UI] Aktualizacja od {sender}: {data}")
