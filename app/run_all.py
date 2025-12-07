import asyncio

from utils.config_loader import load_config, get_agent_credentials
from agents.behavior_and_alarm_agent import BehaviorAndAlarmAgent
from agents.feed_control_agent import FeedControlAgent
from agents.hen_simulator_agent import HenSimulatorAgent
from agents.lighting_agent import LightingAgent
from agents.logger_agent import LoggerAgent
from agents.ui_agent import UIAgent


async def main():
    cfg = load_config()

    agents = []

    for key, cls in [
        ("logger", LoggerAgent),
        ("ui", UIAgent),
        ("behavior_alarm", BehaviorAndAlarmAgent),
        ("lighting", LightingAgent),
        ("feed_control", FeedControlAgent),
        ("hen_simulator", HenSimulatorAgent),
    ]:
        jid, password = get_agent_credentials(key, cfg)
        a = cls(jid, password, verify_security=cfg["xmpp"]["verify_security"])
        await a.start(auto_register=False)
        agents.append(a)
        print(f"{cls.__name__} wystartowany jako {jid}")

    print("Czekam aż wszyscy agenci zalogują się do Prosody...")
    await asyncio.sleep(1.5)

    print("Wszystkie agenty online. CTRL+C aby zakończyć.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Zatrzymuję wszystkich agentów...")
        for a in agents:
            await a.stop()


if __name__ == "__main__":
    asyncio.run(main())
