"""Hook that fires whenever the Necromancer summons a new spirit."""

from pathlib import Path


def run(agent_name: str, workspace: str) -> None:
    crypt = Path(workspace)
    crypt.mkdir(parents=True, exist_ok=True)
    (crypt / ".spirit_log").write_text(f"🧟 {agent_name} claimed {workspace}\n")
