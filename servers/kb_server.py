from __future__ import annotations
from typing import Any
import json
from fastmcp import FastMCP

# In-memory demo data
_DOCS = [
    {"id": "KB-1", "title": "CVX-12 Overheating - First Response", "body": "Check condenser airflow, verify setpoint, inspect coolant levels."},
    {"id": "KB-2", "title": "Vibration Diagnostics - QRT Series", "body": "Check mounting, bearing wear, and imbalance. Review FFT spectrum."},
    {"id": "KB-3", "title": "Sensor Calibration Procedure", "body": "Use reference probe, run calibration routine, confirm offsets."},
]

# Create FastMCP server
mcp = FastMCP("kb")

@mcp.tool()
def kb_query(query: str, k: int = 3) -> dict[str, Any]:
    """Return top-k docs by naive keyword scoring.
    
    Args:
        query: Search query
        k: Number of results to return (default: 3)
    """
    q = query.lower().split()
    scored = []
    for d in _DOCS:
        text = (d["title"] + " " + d["body"]).lower()
        score = sum(1 for token in q if token in text)
        scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits = [d for s, d in scored[:k] if s > 0]
    return {"count": len(hits), "docs": hits}

if __name__ == "__main__":
    # Run with SSE transport on port 8001
    mcp.run(transport="sse", port=8001)