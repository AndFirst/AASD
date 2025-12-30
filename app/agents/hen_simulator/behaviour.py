import json
import random

from spade.behaviour import PeriodicBehaviour, CyclicBehaviour

from utils.messaging import build_message


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _safe_parse_body(body: str):
    """
    build_message prawdopodobnie serializuje dict do JSON w body.
    Żeby było odporne, próbujemy JSON, a jak się nie da, zwracamy None.
    """
    if body is None:
        return None
    if isinstance(body, dict):
        return body
    if not isinstance(body, str):
        return None

    body = body.strip()
    if not body:
        return None

    try:
        return json.loads(body)
    except Exception:
        return None


class ReceiveFeedingBehaviour(CyclicBehaviour):
    """
    Odbiera informację o karmieniu i zmniejsza hunger.
    Zakładamy komunikat:
      performative="inform"
      conversation="feeding"
      content={
          "type": "feed_dispensed",
          "hen_id": "<jid>" | None (None = broadcast)
          "amount": <int>
      }
    """
    async def run(self):
        msg = await self.receive(timeout=1)
        if not msg:
            return

        conv = (msg.metadata or {}).get("conversation")
        if conv != "feeding":
            return

        data = _safe_parse_body(msg.body)
        if not isinstance(data, dict):
            return

        if data.get("type") != "feed_dispensed":
            return

        target_hen = data.get("hen_id")
        if target_hen and target_hen != self.agent.hen_id:
            return

        try:
            amount = int(data.get("amount", 0))
        except Exception:
            amount = 0

        if amount <= 0:
            return

        prev = int(getattr(self.agent.state, "hunger", 0) or 0)
        new_hunger = max(0, prev - amount)
        self.agent.state.hunger = new_hunger

        print(f"[SIM:{self.agent.hen_id}] Nakarmiona: -{amount} hunger ({prev} -> {new_hunger})")


class ReceiveLightingBehaviour(CyclicBehaviour):
    """
    Symulator odbiera aktualny poziom światła, żeby wpływał na aggression.

    Format (uzgodniony):
      conversation="lighting"
      content={
        "type": "light_level_update" | "light_state_update",
        "payload": {"level": <int>, "reason": "...", "hen_id": "...optional..."}
      }

    Jeśli payload.hen_id jest podane, to wiadomość jest per-hen.
    Jeśli nie ma hen_id, traktujemy jako globalną.
    """
    async def run(self):
        msg = await self.receive(timeout=1)
        if not msg:
            return

        conv = (msg.metadata or {}).get("conversation")
        if conv != "lighting":
            return

        data = _safe_parse_body(msg.body)
        if not isinstance(data, dict):
            return

        msg_type = data.get("type")
        if msg_type not in ("light_level_update", "light_state_update"):
            return

        payload = data.get("payload", {}) or {}
        target_hen = payload.get("hen_id")

        # jeśli hen_id jest wskazane i nie pasuje -> ignoruj
        if target_hen and target_hen != self.agent.hen_id:
            return

        try:
            level = int(payload.get("level", self.agent.current_light_level))
        except Exception:
            return

        level = _clamp(level, 0, 100)
        prev = int(self.agent.current_light_level)
        self.agent.current_light_level = level

        if prev != level:
            reason = payload.get("reason", "unknown")
            print(f"[SIM:{self.agent.hen_id}] Światło: level {prev} -> {level} (reason={reason})")


class SimulateBehaviour(PeriodicBehaviour):
    def _compute_light_effect_on_aggression(self) -> int:
        """
        Wpływ światła na aggression (aggression: -10..+10):

        - Za ciemno (level < neutral) => aggression rośnie (w stronę dodatnią)
        - Za jasno  (level > neutral) => aggression spada (w stronę ujemną)

        Czułość:
          co `light_sensitivity` punktów różnicy światła -> ok. 1 punkt aggression

        Żeby nie było “martwej strefy” przez round(),
        robimy:
          magnitude = abs(delta_level) // sens  (min 1 jeśli delta != 0)
          sign = +1 jeśli ciemniej, -1 jeśli jaśniej
        i clamp per tick do +/- max_light_effect_per_tick.
        """
        level = int(self.agent.current_light_level)
        neutral = int(self.agent.neutral_light_level)
        sens = max(1, int(self.agent.light_sensitivity))

        delta = neutral - level  # >0 ciemniej (aggr +), <0 jaśniej (aggr -)
        if delta == 0:
            return 0

        magnitude = abs(delta) // sens
        if magnitude <= 0:
            magnitude = 1  # minimalny efekt jeśli różnica istnieje

        sign = 1 if delta > 0 else -1
        effect = sign * magnitude

        max_eff = int(self.agent.max_light_effect_per_tick)
        effect = _clamp(effect, -max_eff, max_eff)
        return effect

    async def run(self):
        # --- 1) Aktualizacja stanu w czasie (bez resetowania) ---
        prev_hunger = int(getattr(self.agent.state, "hunger", 0) or 0)
        prev_aggr = int(getattr(self.agent.state, "aggression", 0) or 0)

        # Głód narasta
        hunger_inc = random.randint(self.agent.hunger_tick_min, self.agent.hunger_tick_max)
        hunger = _clamp(prev_hunger + hunger_inc, 0, self.agent.hunger_max)

        # --- aggression model: -10..+10 ---
        # Bazowy dryf: hunger podbija aggression dodatnio + szum
        hunger_pressure = 0
        if hunger >= 70:
            hunger_pressure = 2
        elif hunger >= 60:
            hunger_pressure = 1

        noise = random.choice([-1, 0, 0, 1])

        # Wpływ światła
        light_effect = self._compute_light_effect_on_aggression()

        aggr = prev_aggr + hunger_pressure + noise + light_effect
        aggr = _clamp(aggr, self.agent.aggression_min, self.agent.aggression_max)

        self.agent.state.hunger = hunger
        self.agent.state.aggression = aggr

        print(
            f"[SIM:{self.agent.hen_id}] Hunger={hunger} (Δ{hunger_inc}), "
            f"Aggr={aggr} (light={self.agent.current_light_level}, lightΔ={light_effect})"
        )

        # --- 2) Symulator -> FeedControl (inform) ---
        msg_feed = build_message(
            to=self.agent.feed_control_jid,
            performative="inform",
            conversation="feeding",
            content={
                "type": "hunger_update",
                "hen_id": self.agent.hen_id,
                "hunger": hunger,
            },
        )
        await self.send(msg_feed)

        if hunger >= self.agent.hunger_high_threshold:
            msg_hunger_high = build_message(
                to=self.agent.feed_control_jid,
                performative="inform",
                conversation="feeding",
                content={
                    "type": "hunger_high",
                    "hen_id": self.agent.hen_id,
                    "hunger": hunger,
                    "threshold": self.agent.hunger_high_threshold,
                },
            )
            await self.send(msg_hunger_high)

        # --- 3) Symulator -> BehaviorAndAlarm (inform) ---
        msg_behavior = build_message(
            to=self.agent.behavior_alarm_jid,
            performative="inform",
            conversation="behavior",
            content={
                "type": "behavior_update",
                "hen_id": self.agent.hen_id,
                "hunger": hunger,
                "aggression": aggr,
            },
        )
        await self.send(msg_behavior)

        # Zdarzenie progowe: agresja dodatnia (tylko dodatnia, jak w Twoim założeniu)
        if aggr >= self.agent.aggression_threshold:
            msg_aggr = build_message(
                to=self.agent.behavior_alarm_jid,
                performative="inform",
                conversation="behavior",
                content={
                    "type": "aggression_detected",
                    "hen_id": self.agent.hen_id,
                    "aggression": aggr,
                    "threshold": self.agent.aggression_threshold,
                    "hunger": hunger,
                },
            )
            await self.send(msg_aggr)

        # --- 4) Symulator -> UI (inform/update_state) ---
        msg_ui = build_message(
            to=self.agent.ui_jid,
            performative="inform",
            conversation="update_state",
            content={
                "type": "hen_state_update",
                "source": self.agent.hen_id,
                "payload": {
                    "hen_id": self.agent.hen_id,
                    "hunger": hunger,
                    "aggression": aggr,
                },
            },
        )
        await self.send(msg_ui)
