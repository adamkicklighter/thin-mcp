from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging
import httpx
import asyncio
import uuid

from host.tenant_policy import TENANTS
from host.types import ToolSpec, ToolCallTrace
from host.oai_router import OAIRouter

logger = logging.getLogger(__name__)

@dataclass
class OrchestratorResult:
    selected_tool: str
    trace: List[ToolCallTrace]
    result: Any

class FastMCPClient:
    """Client for FastMCP servers using SSE."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.messages_endpoint = None
        self.session_id = None
        self.response_queue = asyncio.Queue()
        self.sse_task = None
        
    async def _listen_sse(self, client: httpx.AsyncClient):
        """Listen to SSE stream for responses."""
        try:
            async with client.stream("GET", f"{self.base_url}/sse", timeout=None) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("event: endpoint"):
                        continue
                    elif line.startswith("data: "):
                        data = line[6:].strip()
                        
                        # First message is the endpoint
                        if data.startswith("/messages/"):
                            self.messages_endpoint = f"{self.base_url}{data}"
                            # Extract session ID from endpoint
                            self.session_id = data.split("session_id=")[1]
                            logger.info(f"  Got session: {self.session_id}")
                            await self.response_queue.put({"type": "endpoint", "data": data})
                        else:
                            # JSON-RPC response
                            try:
                                json_data = json.loads(data)
                                await self.response_queue.put(json_data)
                            except json.JSONDecodeError:
                                logger.warning(f"  Could not parse SSE data: {data}")
        except Exception as e:
            logger.error(f"  SSE listener error: {e}")
            await self.response_queue.put({"error": str(e)})
    
    async def connect(self, client: httpx.AsyncClient):
        """Start SSE connection."""
        if self.sse_task:
            return
            
        logger.info(f"  Starting SSE connection to {self.base_url}...")
        
        # Start SSE listener in background
        self.sse_task = asyncio.create_task(self._listen_sse(client))
        
        # Wait for endpoint message
        try:
            msg = await asyncio.wait_for(self.response_queue.get(), timeout=5.0)
            if msg.get("type") != "endpoint":
                raise ConnectionError(f"Expected endpoint message, got: {msg}")
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout waiting for endpoint from {self.base_url}")
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "thin-mcp-orchestrator",
                    "version": "1.0.0"
                }
            }
        }
        
        # Post to messages endpoint
        post_response = await client.post(
            self.messages_endpoint,
            json=init_request,
            timeout=10.0
        )
        post_response.raise_for_status()
        
        # Wait for initialize response on SSE
        try:
            response = await asyncio.wait_for(self.response_queue.get(), timeout=10.0)
            if "error" in response:
                raise Exception(f"Initialize error: {response['error']}")
            logger.info(f"  ✓ Session initialized")
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout waiting for initialize response from {self.base_url}")
        
    async def list_tools(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """List available tools from the server."""
        await self.connect(client)
        
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {}
        }
        
        # Send request
        post_response = await client.post(
            self.messages_endpoint,
            json=request,
            timeout=10.0
        )
        post_response.raise_for_status()
        
        # Wait for response on SSE
        try:
            response = await asyncio.wait_for(self.response_queue.get(), timeout=10.0)
            if "error" in response:
                raise Exception(f"MCP error: {response['error']}")
            return response.get("result", {}).get("tools", [])
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout waiting for tools/list response")
    
    async def call_tool(self, client: httpx.AsyncClient, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server."""
        await self.connect(client)
        
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Send request
        post_response = await client.post(
            self.messages_endpoint,
            json=request,
            timeout=30.0
        )
        post_response.raise_for_status()
        
        # Wait for response on SSE
        try:
            response = await asyncio.wait_for(self.response_queue.get(), timeout=30.0)
            if "error" in response:
                raise Exception(f"MCP error: {response['error']}")
            return response.get("result", {})
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout waiting for tools/call response")
    
    async def close(self):
        """Close the SSE connection."""
        if self.sse_task:
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass

class MCPOrchestrator:
    def __init__(self, router: OAIRouter):
        self.router = router
        self.servers = {
            "tickets": FastMCPClient("http://127.0.0.1:8000"),
            "kb": FastMCPClient("http://127.0.0.1:8001")
        }

    async def _discover_tools(self, client: httpx.AsyncClient) -> List[ToolSpec]:
        """Discover tools from all FastMCP servers."""
        tools: List[ToolSpec] = []
        
        for server_name, mcp_client in self.servers.items():
            logger.info(f"Discovering tools from {server_name}...")
            try:
                server_tools = await mcp_client.list_tools(client)
                logger.info(f"  ✓ Found {len(server_tools)} tools from {server_name}")
                
                for tool in server_tools:
                    tool_id = f"{server_name}.{tool['name']}"
                    tools.append(
                        ToolSpec(
                            tool_id=tool_id,
                            description=tool.get('description', ''),
                            input_schema=tool.get('inputSchema', {"type": "object", "properties": {}}),
                        )
                    )
            except Exception as e:
                logger.error(f"  ✗ Failed to discover tools from {server_name}: {e}")
                raise ConnectionError(f"Cannot connect to {server_name} server at {mcp_client.base_url}. Is it running?")
        
        return tools

    async def invoke(self, tenant_id: str, user_input: str) -> OrchestratorResult:
        logger.info(f"Starting orchestration for tenant: {tenant_id}")
        policy = TENANTS.get(tenant_id)
        if not policy:
            raise ValueError(f"Unknown tenant: {tenant_id}")

        logger.info("Connecting to FastMCP servers...")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Discover tools
                logger.info("Discovering available tools...")
                tool_specs = await self._discover_tools(client)
                logger.info(f"✓ Found {len(tool_specs)} tools total: {[t.tool_id for t in tool_specs]}")

                # Enforce tenant allowlist at the catalog level
                allowed = [t for t in tool_specs if t.tool_id in policy.allowed_tools]
                if not allowed:
                    raise PermissionError("No tools allowed for this tenant.")
                
                logger.info(f"✓ Policy allows {len(allowed)} tools for tenant '{tenant_id}'")

                logger.info("Calling LLM router to select tool...")
                decision = self.router.choose_tool(user_input, allowed)
                logger.info(f"✓ Router selected: {decision.tool_id}")
                logger.info(f"  Args: {decision.args}")
                
                if decision.tool_id not in policy.allowed_tools:
                    raise PermissionError(f"Tool denied by policy: {decision.tool_id}")

                # Map tool_id -> server + tool name
                server_name, tool_name = decision.tool_id.split(".", 1)
                mcp_client = self.servers[server_name]

                trace: List[ToolCallTrace] = []
                try:
                    logger.info(f"Invoking {tool_name} on {server_name} server...")
                    result = await mcp_client.call_tool(client, tool_name, decision.args)
                    logger.info(f"✓ Tool execution successful")

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
                    logger.error(f"✗ Tool call failed: {e}", exc_info=True)
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
            # Clean up SSE connections
            for mcp_client in self.servers.values():
                await mcp_client.close()