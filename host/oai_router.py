from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from host.types import ToolSpec

class RouteDecision(BaseModel):
    tool_id: str = Field(..., description="Must be one of the provided tool_ids.")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments matching the tool's JSON schema.")

class OAIRouter:
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    def _make_strict_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add additionalProperties: false to all objects in schema for strict mode."""
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                schema["additionalProperties"] = False
            for key, value in schema.items():
                if isinstance(value, dict):
                    self._make_strict_schema(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._make_strict_schema(item)
        return schema

    async def choose_tool(self, user_input: str, tools: List[ToolSpec]) -> RouteDecision:
        # Compact tool list for the model
        tool_brief = [
            {
                "tool_id": t.tool_id,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

        schema = RouteDecision.model_json_schema()
        # Make schema strict for OpenAI structured outputs
        schema = self._make_strict_schema(schema)

        prompt = (
            "You are a routing controller. Choose exactly one tool to call.\n"
            "Rules:\n"
            "- tool_id MUST match one of the provided tool_ids.\n"
            "- args MUST satisfy the chosen tool's input_schema.\n"
            "- If the request is informational, prefer kb.kb_query.\n"
            "- If the request is operational on tickets, prefer tickets.* tools.\n"
        )

        # Use chat completions API with response_format for structured outputs
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"User request: {user_input}\n\nAvailable tools:\n{json.dumps(tool_brief, indent=2)}"},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "route_decision",
                    "schema": schema,
                    "strict": True
                }
            }
        )

        # Extract the JSON content from the response
        content = resp.choices[0].message.content
        decision = RouteDecision.model_validate_json(content)
        return decision