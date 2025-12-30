import asyncio
from spade.agent import Agent

from agents.lighting.lighting_agent_behaviour import LightningBehaviour
from models.environment_state import LightingState
from utils.config_loader import load_config, get_agent_credentials


class LightingAgent(Agent):
    def __init__(self, jid: str, password: str, port: int = 5222, verify_security: bool = False):
        super().__init__(jid, password, port, verify_security)

        self.logger_jid: str | None = None
        self.ui_jid: str | None = None

        # ile kur w symulacji (do init per-hen)
        self.hen_count: int = 5

        # --- PER-HEN stan światła ---
        # level dla każdej kury osobno
        self.hen_light_levels: dict[str, int] = {}

        # config (regulator)
        self.neutral_level: int = 50
        self.min_level: int = 0
        self.max_level: int = 100

        # “idealny” zakres aggression
        self.target_aggr_min: int = -3
        self.target_aggr_max: int = 3

        # regulator typu setpoint:
        # target = neutral + gain * aggression
        self.gain_per_aggression: float = 4.0

        # antyspam
        self.min_delta_to_send: int = 2          # nie wysyłaj jak zmiana < 2
        self.min_update_interval_s: float = 1.0  # nie częściej niż raz na X sek

        # te pola są “runtime” używane przez behaviour
        self._last_sent_level: dict[str, int] = {}   # hen_id -> last sent level
        self._last_set_at: dict[str, float] = {}     # hen_id -> monotonic timestamp

        # (zostawiamy żeby model environment_state się nie wywalił jeśli coś oczekuje .light_state)
        # ale NIE używamy globalnego poziomu w regulatorze
        self.light_state: LightingState | None = None

    async def setup(self):
        print("[LIGHT] Agent uruchomiony.")
        cfg = load_config()

        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.logger_jid = cfg["agents"]["logger"]["jid"]

        sim_cfg = cfg.get("hen_simulator", {}) or {}
        self.hen_count = int(sim_cfg.get("count", self.hen_count))

        light_cfg = cfg.get("lighting", {}) or {}
        self.neutral_level = int(light_cfg.get("neutral_level", self.neutral_level))
        self.min_level = int(light_cfg.get("min_level", self.min_level))
        self.max_level = int(light_cfg.get("max_level", self.max_level))

        self.target_aggr_min = int(light_cfg.get("target_aggr_min", self.target_aggr_min))
        self.target_aggr_max = int(light_cfg.get("target_aggr_max", self.target_aggr_max))

        self.gain_per_aggression = float(light_cfg.get("gain_per_aggression", self.gain_per_aggression))
        self.min_delta_to_send = int(light_cfg.get("min_delta_to_send", self.min_delta_to_send))
        self.min_update_interval_s = float(light_cfg.get("min_update_interval_s", self.min_update_interval_s))

        # clamp neutral
        self.neutral_level = max(self.min_level, min(self.max_level, self.neutral_level))

        # init map per-hen
        for i in range(1, self.hen_count + 1):
            hen_id = f"simulator{i}@localhost"
            self.hen_light_levels[hen_id] = int(self.neutral_level)

        # “global” stan tylko informacyjnie
        self.light_state = LightingState(level=int(self.neutral_level))

        # UWAGA: Agent NIC NIE WYSYŁA. Wszystko w Behaviour.
        self.add_behaviour(LightningBehaviour())


async def main():
    cfg = load_config()
    jid, password = get_agent_credentials("lighting", cfg)

    agent = LightingAgent(jid, password, verify_security=cfg["xmpp"]["verify_security"])
    await agent.start(auto_register=False)
    print("LightingAgent jest online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję LightingAgent...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
