from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from host.tenant_policy import TENANTS
from host.types import ToolSpec, ToolCallTrace
from host.oai_router import OAIRouter

# MCP client imports (official SDK)
# The MCP Python SDK supports building MCP clients and servers. :contentReference[oaicite:6]{index=6}
from mcp import ClientSession
from mcp.client.stdio import stdio_client

@dataclass
class OrchestratorResult:
    selected_tool: str
    trace: List[ToolCallTrace]
    result: Any

class MCPOrchestrator:
    def __init__(self, router: OAIRouter):
        self.router = router

    async def _connect_servers(self) -> List[Tuple[str, ClientSession]]:
        """
        For POC: start MCP servers via stdio subprocess.
        """
        servers = []

        # tickets server
        tickets_transport = await stdio_client("python", ["-m", "mcp_servers.tickets_server"])
        tickets_session = ClientSession(tickets_transport)
        await tickets_session.initialize()
        servers.append(("tickets", tickets_session))

        # kb server
        kb_transport = await stdio_client("python", ["-m", "mcp_servers.kb_server"])
        kb_session = ClientSession(kb_transport)
        await kb_session.initialize()
        servers.append(("kb", kb_session))

        return servers

    async def _discover_tools(self, sessions: List[Tuple[str, ClientSession]]) -> List[ToolSpec]:
        tools: List[ToolSpec] = []
        for server_name, sess in sessions:
            resp = await sess.list_tools()
            for t in resp.tools:
                # tool_id namespaced by server for demo clarity
                tool_id = f"{server_name}.{t.name}"
                tools.append(
                    ToolSpec(
                        tool_id=tool_id,
                        description=t.description or "",
                        input_schema=(t.inputSchema or {"type": "object", "properties": {}}),
                    )
                )
        return tools

    async def invoke(self, tenant_id: str, user_input: str) -> OrchestratorResult:
        policy = TENANTS.get(tenant_id)
        if not policy:
            raise ValueError(f"Unknown tenant: {tenant_id}")

        sessions = await self._connect_servers()
        try:
            tool_specs = await self._discover_tools(sessions)

            # Enforce tenant allowlist at the catalog level
            allowed = [t for t in tool_specs if t.tool_id in policy.allowed_tools]
            if not allowed:
                raise PermissionError("No tools allowed for this tenant.")

            decision = self.router.choose_tool(user_input, allowed)
            if decision.tool_id not in policy.allowed_tools:
                raise PermissionError(f"Tool denied by policy: {decision.tool_id}")

            # Map tool_id -> session + tool name
            server_name, tool_name = decision.tool_id.split(".", 1)
            sess = dict(sessions)[server_name]

            trace: List[ToolCallTrace] = []
            try:
                call = await sess.call_tool(tool_name, decision.args)
                result = call.content

                trace.append(
                    ToolCallTrace(
                        tool_id=decision.tool_id,
                        args=decision.args,
                        ok=True,
                        error=None,
                        result_preview=str(result)[:300],
                    )
                )
                return OrchestratorResult(selected_tool=decision.tool_id, trace=trace, result=result)
            except Exception as e:
                trace.append(
                    ToolCallTrace(
                        tool_id=decision.tool_id,
                        args=decision.args,
                        ok=False,
                        error=str(e),
                        result_preview="",
                    )
                )
                raise
        finally:
            # Close sessions/transports
            for _, sess in sessions:
                try:
                    await sess.close()
                except Exception:
                    pass