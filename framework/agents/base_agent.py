"""Base class for every NecroCode spirit."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class BaseSpirit:
    role: str
    skills: List[str]
    workspace: str = "workspace1"
    identifier: str = field(init=False)

    def __post_init__(self) -> None:
        self.identifier = f"{self.role}_spirit"

    def chant(self, message: str) -> str:
        return f"💀 {self.identifier}: {message}"
