"""Database specialist spirit."""

from .base_agent import BaseSpirit


class DatabaseSpirit(BaseSpirit):
    def weave_schema(self) -> str:
        return self.chant("Etching schemas into obsidian tablets...")
