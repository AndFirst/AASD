import asyncio
from time import sleep

from spade.agent import Agent


class BaseAgent(Agent):
    """Bazowa klasa agenta SPADE z obsługą reconnect i lifecycle logs."""

    def __init__(self, jid: str, password: str, host: str = "localhost"):
        # Jeśli jid nie zawiera domeny, dołącz host automatycznie
        if "@" not in jid:
            jid = f"{jid}@{host}"

        self.host = host
        print(f"[INIT] {jid} {password}")
        super().__init__(jid, password)

    async def start(self, auto_register: bool = True) -> None:
        """Próbuje połączyć się z serwerem XMPP do skutku."""
        print(f"[START] Connecting {self.jid}...")
        while True:
            try:
                await super().start(auto_register)
                print(f"[OK] {self.jid} connected.")
                break
            except Exception as e:
                print(f"[ERR] {self.jid} connection failed: {e}")
                print("Retrying in 3 seconds...")
                sleep(3)

    async def stop(self):
        """Zatrzymuje agenta z logami stanu."""
        if not self.is_alive():
            print(f"[STOP] {self.jid} is already stopped.")
        else:
            print(f"[STOP] Stopping {self.jid}...")
        return await super().stop()

    async def setup(self):
        """Domyślny setup agenta — można nadpisać w klasach pochodnych."""
        print(f"[SETUP] {self.jid} setup started.")
        await asyncio.sleep(0.1)
        print(f"[SETUP] {self.jid} ready.")
