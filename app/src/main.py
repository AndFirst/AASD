import importlib
import json
from pathlib import Path

import spade
from pydantic import BaseModel
from spade.agent import Agent

import spade_patch  # noqa: F401

CONFIG_FILE = "config.json"


def init_database(config):
    pass


class AgentConfig(BaseModel):
    class_: str
    jid: str
    password: str


class AppConfig(BaseModel):
    agents: list[AgentConfig]


def get_class_by_name(module_name: str, class_name: str):
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


async def init_agents(config: AppConfig) -> list[Agent]:
    agents = []
    for agent_conf in config["agents"]:
        cls = get_class_by_name("agents", agent_conf["class_"])
        agent = cls(agent_conf["jid"], agent_conf["password"])
        agents.append(agent)
        await agent.start()
    return agents


def get_config(config_file: Path) -> AppConfig:
    with open(config_file, "r") as f:
        return json.load(f)


async def main() -> None:
    config_file = Path(__file__).parent / CONFIG_FILE
    config = get_config(config_file)
    agents = await init_agents(config)
    await spade.wait_until_finished(agents)


if __name__ == "__main__":
    spade.run(main())
