from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tickets")

# In-memory demo data
_TICKETS = [
    {"id": "T-1001", "asset": "CVX-12", "status": "open", "created_at": "2026-01-15", "summary": "Overheating alarm"},
    {"id": "T-1002", "asset": "CVX-12", "status": "closed", "created_at": "2026-01-10", "summary": "Sensor calibration"},
    {"id": "T-1003", "asset": "QRT-9", "status": "open", "created_at": "2026-01-18", "summary": "Vibration anomaly"},
]

@mcp.tool()
def tickets_search(query: str, days: int = 30) -> Dict[str, Any]:
    """
    Search tickets by naive keyword matching and a 'days' time window.
    """
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    q = query.lower()

    def keep(t: Dict[str, Any]) -> bool:
        created = datetime.strptime(t["created_at"], "%Y-%m-%d").date()
        if created < cutoff:
            return False
        blob = f'{t["id"]} {t["asset"]} {t["status"]} {t["summary"]}'.lower()
        return q in blob

    hits = [t for t in _TICKETS if keep(t)]
    return {"count": len(hits), "tickets": hits}

@mcp.tool()
def tickets_create(asset: str, summary: str, priority: str = "medium") -> Dict[str, Any]:
    """
    Create a ticket (in-memory).
    """
    new_id = f"T-{1000 + len(_TICKETS) + 1}"
    ticket = {
        "id": new_id,
        "asset": asset,
        "status": "open",
        "created_at": datetime.utcnow().date().isoformat(),
        "summary": summary,
        "priority": priority,
    }
    _TICKETS.append(ticket)
    return {"created": True, "ticket": ticket}