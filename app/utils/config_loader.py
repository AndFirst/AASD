import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    config_path = BASE_DIR / "config" / "config.json"
    with config_path.open(encoding="utf-8") as f:
        return json.load(f)


def get_agent_credentials(name: str, cfg: dict | None = None) -> tuple[str, str]:
    if cfg is None:
        cfg = load_config()
    agent_cfg = cfg["agents"][name]
    return agent_cfg["jid"], agent_cfg["password"]
