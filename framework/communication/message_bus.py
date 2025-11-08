"""Lightweight message bus between spirits."""

from dataclasses import dataclass, field
from typing import Callable, List

from .protocol import AgentMessage


@dataclass
class MessageBus:
    spirits: List
    handlers: List[Callable[[AgentMessage], None]] = field(default_factory=list)

    def __init__(self) -> None:
        self.spirits = []
        self.handlers = []

    def register(self, spirit) -> None:
        self.spirits.append(spirit)

    def subscribe(self, handler: Callable[[AgentMessage], None]) -> None:
        self.handlers.append(handler)

    def dispatch(self, message: AgentMessage) -> None:
        for handler in self.handlers:
            handler(message)
