from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set

@dataclass(frozen=True)
class TenantLimits:
    max_calls_per_request: int = 2

@dataclass(frozen=True)
class TenantPolicy:
    allowed_tools: Set[str]
    limits: TenantLimits

TENANTS: Dict[str, TenantPolicy] = {
    "acme": TenantPolicy(
        allowed_tools={"tickets.tickets_search", "kb.kb_query"},
        limits=TenantLimits(max_calls_per_request=2),
    ),
    "globex": TenantPolicy(
        allowed_tools={"tickets.tickets_search", "tickets.tickets_create", "kb.kb_query"},
        limits=TenantLimits(max_calls_per_request=2),
    ),
}