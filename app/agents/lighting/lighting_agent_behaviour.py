from spade.behaviour import CyclicBehaviour

from utils.messaging import parse_content, build_message


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
