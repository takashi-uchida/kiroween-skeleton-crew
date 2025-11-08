"""Frontend specialist spirit."""

from .base_agent import BaseSpirit


class FrontendSpirit(BaseSpirit):
    def summon_ui(self) -> str:
        return self.chant("Sketching spectral UI components...")
