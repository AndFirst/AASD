from spade.agent import Agent

from agents.ui.ui_agent_behaviour import ReceiveBehaviour
from agents.ui.ui_ws import UiWebSocketHub, start_ws_server


class UIAgent(Agent):
    async def setup(self):
        print("[UI] Agent uruchomiony.")

        self.hens: dict[str, dict] = {}
        self.feed: dict = {}
        self.lights_by_hen: dict[str, dict] = {}
        self.last_events: list[dict] = []

        hub = UiWebSocketHub()
        await start_ws_server(hub, host="0.0.0.0", port=8765)
        recv_beh = ReceiveBehaviour(
            ws_hub=hub,
            render_interval_sec=0.5,
            dedup_window_sec=3.0,
            also_print_console=False,
        )
        self.add_behaviour(recv_beh)
