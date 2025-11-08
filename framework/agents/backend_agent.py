"""Backend specialist spirit."""

from .base_agent import BaseSpirit


class BackendSpirit(BaseSpirit):
    def forge_api(self) -> str:
        return self.chant("Binding REST sigils and WebSocket wards...")
