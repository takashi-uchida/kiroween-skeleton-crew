"""Creates spirit instances from role requests."""

from typing import List

from framework.agents import base_agent, frontend_agent, backend_agent, database_agent, devops_agent

SPIRIT_REGISTRY = {
    "frontend": frontend_agent.FrontendSpirit,
    "backend": backend_agent.BackendSpirit,
    "database": database_agent.DatabaseSpirit,
    "devops": devops_agent.DevOpsSpirit,
}


def summon(role_requests: List[str]):
    spirits = []
    for request in role_requests:
        spirit_cls = SPIRIT_REGISTRY.get(request.name, base_agent.BaseSpirit)
        spirits.append(spirit_cls(role=request.name, skills=request.skills))
    return spirits
