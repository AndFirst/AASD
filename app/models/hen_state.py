from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HenState:
    hunger: int = 0  # 0 – 100
    aggression: int = 0  # -10 – 10
    timestamp: datetime = field(default_factory=datetime.now)
