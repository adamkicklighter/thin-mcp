from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class ToolSpec:
    tool_id: str          # e.g. "tickets.tickets_search"
    description: str
    input_schema: Dict[str, Any]

@dataclass
class ToolCallTrace:
    tool_id: str
    args: Dict[str, Any]
    ok: bool
    error: Optional[str]
    result_preview: str