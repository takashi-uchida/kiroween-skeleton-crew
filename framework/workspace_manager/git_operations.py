"""Small wrapper around git commands for spirits."""

import subprocess
from pathlib import Path
from typing import Sequence


class GitOperations:
    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    def run(self, *args: Sequence[str]) -> None:
        subprocess.run(["git", *args], check=True, cwd=self.cwd)
