from dataclasses import dataclass


@dataclass
class FeedState:
    level: int
    capacity: int


@dataclass
class LightingState:
    level: int
