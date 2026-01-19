from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple

from openai import OpenAI
from pydantic import BaseModel, Field

from host.types import ToolSpec

class RouteDecision(BaseModel):
    tool_id: str = Field(..., description="Must be one of the provided tool_ids.")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments matching the tool's JSON schema.")

class OAIRouter:
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def choose_tool(self, user_input: str, tools: List[ToolSpec]) -> RouteDecision:
        # Compact tool list for the model
        tool_brief = [
            {
                "tool_id": t.tool_id,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

        schema = {
            "name": "route_decision",
            "schema": RouteDecision.model_json_schema(),
            "strict": True,
        }

        prompt = (
            "You are a routing controller. Choose exactly one tool to call.\n"
            "Rules:\n"
            "- tool_id MUST match one of the provided tool_ids.\n"
            "- args MUST satisfy the chosen tool's input_schema.\n"
            "- If the request is informational, prefer kb.kb_query.\n"
            "- If the request is operational on tickets, prefer tickets.* tools.\n"
        )

        # Responses API supports structured outputs and tool-style JSON responses. :contentReference[oaicite:4]{index=4}
        resp = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"User request: {user_input}\n\nAvailable tools:\n{json.dumps(tool_brief, indent=2)}"},
            ],
            text={"format": {"type": "json_schema", "json_schema": schema}},
        )

        # The SDK returns structured content under resp.output_text for json_schema text output
        decision = RouteDecision.model_validate_json(resp.output_text)
        return decision