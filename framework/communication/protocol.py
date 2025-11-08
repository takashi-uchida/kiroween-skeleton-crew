"""Spirit Protocol primitives."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    workspace: str
    message_type: str
    payload: Dict
    timestamp: datetime = datetime.utcnow()
