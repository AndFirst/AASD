import asyncio

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from models.environment_state import LightingState
from utils.config_loader import load_config, get_agent_credentials
from utils.messaging import build_message, parse_content


class LightingAgent(Agent):
    class ControlBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            content = parse_content(msg)
            conv = msg.get_metadata("conversation")
            if conv != "lighting":
                return

            msg_type = content.get("type")

            if msg_type == "calm_hens":
                self.agent.light_state.mode = "calm"
                self.agent.light_state.level = self.agent.calm_level
                reason = "calm_hens"

            elif msg_type == "set_light":
                level = int(content.get("level", self.agent.normal_level))
                self.agent.light_state.mode = "manual"
                self.agent.light_state.level = level
                reason = "manual_set"
            else:
                return

            print(f"[LIGHT] Zmiana światła: {self.agent.light_state}")
            await self.notify_state_change(reason)

        async def notify_state_change(self, reason: str):
            payload = {
                "event_type": "light_change",
                "payload": {
                    "level": self.agent.light_state.level,
                    "mode": self.agent.light_state.mode,
                    "reason": reason,
                },
            }

            # inform → UIAgent
            msg_ui = build_message(
                to=self.agent.ui_jid,
                performative="inform",
                conversation="ui_update",
                content=payload,
            )
            await self.send(msg_ui)

            # inform → LoggerAgent
            msg_log = build_message(
                to=self.agent.logger_jid,
                performative="inform",
                conversation="lighting",
                content=payload,
            )
            await self.send(msg_log)

    # --------------------------
    # Agent setup
    # --------------------------
    async def setup(self):
        print("[LIGHT] Agent uruchomiony.")
        cfg = load_config()
        light_cfg = cfg["lighting"]

        self.normal_level = light_cfg["normal_level"]
        self.calm_level = light_cfg["calm_level"]
        self.light_state = LightingState(level=self.normal_level, mode="normal")

        self.ui_jid = cfg["agents"]["ui"]["jid"]
        self.logger_jid = cfg["agents"]["logger"]["jid"]

        self.add_behaviour(self.ControlBehaviour())


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
