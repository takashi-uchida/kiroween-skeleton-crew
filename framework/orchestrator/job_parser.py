"""Parses mortal job descriptions into structured role requests."""

from dataclasses import dataclass
from typing import List


@dataclass
class RoleRequest:
    name: str
    skills: List[str]


class JobParser:
    def parse(self, description: str) -> List[RoleRequest]:
        lines = [line.strip() for line in description.splitlines() if line.strip()]
        requests = []
        for line in lines:
            skills = [skill.strip() for skill in line.split(",") if skill.strip()]
            requests.append(RoleRequest(name=line.split()[0].lower(), skills=skills))
        return requests
