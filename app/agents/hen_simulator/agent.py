import asyncio

from spade.agent import Agent

from agents.hen_simulator.behaviour import SimulateBehaviour, ReceiveFeedingBehaviour, ReceiveLightingBehaviour
from models.hen_state import HenState
from utils.config_loader import load_config, get_agent_credentials


class HenSimulatorAgent(Agent):
    def __init__(
            self, jid: str,
            password: str,
            port: int = 5222,
            verify_security: bool = False
    ):
        super().__init__(jid, password, port, verify_security)

        self.state: HenState | None = None

        self.feed_control_jid: str | None = None
        self.behavior_alarm_jid: str | None = None
        self.ui_jid: str | None = None

        # Każdy symulator = jedna kura
        self.hen_id: str = str(jid)

        # Parametry symulacji głodu
        self.hunger_tick_min: int = 1
        self.hunger_tick_max: int = 5
        self.hunger_max: int = 100

        # Aggression: -10..+10
        self.aggression_min: int = -10
        self.aggression_max: int = 10

        # Progi zdarzeń
        self.hunger_high_threshold: int = 70
        self.aggression_threshold: int = 7  # próg alarmu (po stronie symulatora dla dodatniej agresji)

        # --- Światło (wpływ na aggression) ---
        self.current_light_level: int = 50

        # Neutralny poziom światła (0 wpływu)
        self.neutral_light_level: int = 50

        # Czułość światła: ile punktów światła = ~1 punkt aggression
        self.light_sensitivity: int = 10

        # Limit wpływu światła na tick (żeby nie skakało)
        self.max_light_effect_per_tick: int = 2

    async def setup(self):
        print(f"[SIM:{self.hen_id}] Agent uruchomiony.")
        self.state = HenState()

        # Startowe wartości (ciągła symulacja, bez resetu)
        self.state.hunger = 0
        self.state.aggression = 0

        cfg = load_config()
        self.feed_control_jid = cfg["agents"]["feed_control"]["jid"]
        self.behavior_alarm_jid = cfg["agents"]["behavior_alarm"]["jid"]
        self.ui_jid = cfg["agents"]["ui"]["jid"]

        # (opcjonalnie) konfiguracja symulatora
        sim_cfg = (cfg.get("hen_simulator") or {})

        # ważne: to jest "co kura widzi" na starcie, zanim przyjdzie update od LightingAgenta
        self.current_light_level = int(sim_cfg.get("initial_light_level", self.current_light_level))

        self.neutral_light_level = int(sim_cfg.get("neutral_light_level", self.neutral_light_level))
        self.light_sensitivity = int(sim_cfg.get("light_sensitivity", self.light_sensitivity))
        self.max_light_effect_per_tick = int(sim_cfg.get("max_light_effect_per_tick", self.max_light_effect_per_tick))

        # 1) cykliczna symulacja
        self.add_behaviour(SimulateBehaviour(period=5))
        # 2) asynchroniczny odbiór karmienia (zmniejsza hunger)
        self.add_behaviour(ReceiveFeedingBehaviour())
        # 3) asynchroniczny odbiór zmian światła (wpływa na aggression)
        self.add_behaviour(ReceiveLightingBehaviour())


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
