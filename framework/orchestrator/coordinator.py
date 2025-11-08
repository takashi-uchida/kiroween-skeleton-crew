"""Keeps spirits aligned via the Spirit Protocol."""

from framework.communication.protocol import AgentMessage
from framework.communication.message_bus import MessageBus


class Coordinator:
    def __init__(self, bus: MessageBus | None = None) -> None:
        self.bus = bus or MessageBus()

    def broadcast(self, payload: dict) -> None:
        for spirit in self.bus.spirits:
            message = AgentMessage(
                sender="necromancer",
                receiver=spirit.identifier,
                workspace=spirit.workspace,
                message_type="summoning",
                payload=payload,
            )
            self.bus.dispatch(message)
