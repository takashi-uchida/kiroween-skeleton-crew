"""DevOps specialist spirit."""

from .base_agent import BaseSpirit


class DevOpsSpirit(BaseSpirit):
    def deploy(self) -> str:
        return self.chant("Conjuring Docker phylacteries and CI wards...")
