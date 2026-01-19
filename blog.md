# Building a Thin LLM-Mediated Orchestration Layer for MCP Servers

The Model Context Protocol (MCP) has emerged as a powerful standard for connecting AI applications to external data sources and tools. But as you scale to multiple MCP servers across multi-tenant environments, you face critical questions: How do you route requests to the right server? How do you enforce access control? How do you maintain observability without building a heavyweight orchestration platform?

This post introduces a **thin orchestration layer** that solves these challenges using an LLM as an intelligent router—all while keeping policy enforcement, multi-tenancy, and observability firmly outside the model's control.

## The Problem: Multiple MCP Servers, One User Request

Imagine you're building an enterprise AI assistant that needs to access multiple backend systems:
- A **tickets server** that can search and create support tickets
- A **knowledge base server** that answers questions from internal documentation
- Additional servers for CRM, analytics, or other domain-specific tools

Each system exposes its capabilities as an MCP server. When a user asks "What's the first response for CVX-12 overheating?", how does your application know to route that to the knowledge base server rather than the tickets server? And how do you ensure that the "acme" tenant can't call tools that only "globex" is authorized to use?

## The Architecture: Three Layers of Control

The solution consists of three distinct layers, each with a specific responsibility:

### 1. **The MCP Client Layer** (`FastMCPClient`)

At the foundation is a client that speaks the MCP protocol over Server-Sent Events (SSE). This client handles the low-level details of the MCP lifecycle:

- **Session Management**: Establishes SSE connections, exchanges the `initialize` handshake, and maintains session state
- **Tool Discovery**: Calls `tools/list` to fetch available tools from each MCP server
- **Tool Invocation**: Executes `tools/call` with the appropriate arguments and returns results

The key innovation here is the **async queue pattern** for handling SSE streams—incoming JSON-RPC responses are queued and matched to outgoing requests, allowing multiple servers to be managed concurrently.

```python
class FastMCPClient:
    """Client for FastMCP servers using SSE transport."""
    
    async def list_tools(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Discover tools via MCP tools/list method."""
        # ... JSON-RPC request over SSE
        
    async def call_tool(self, client: httpx.AsyncClient, 
                       tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute tool via MCP tools/call method."""
        # ... JSON-RPC request over SSE
```

### 2. **The LLM Router** (`OAIRouter`)

Once tools are discovered from all servers, the orchestrator needs to decide which tool to call. This is where the LLM comes in—but in a strictly controlled, non-agentic role.

The router:

- Receives the filtered list of tools (already constrained by policy)
- Uses OpenAI's Structured Outputs with JSON Schema and strict mode
- Returns a single `RouteDecision` containing exactly one `tool_id` and its arguments

The routing prompt is deliberately simple:

> "Given these available tools and the user's request, select exactly one tool to call and provide its arguments."

This is not an agentic workflow—there's no reasoning loop, no chain-of-thought, no multi-turn planning. The model simply maps natural language to a tool call within the constraints it's given.

### 3. **The Policy and Orchestration Layer** (`MCPOrchestrator` + `TenantPolicy`)

The orchestrator coordinates the entire flow while enforcing strict governance:

**Policy Enforcement:**

```python
TENANT_POLICIES = {
    "globex": TenantPolicy(
        tenant_id="globex",
        allowed_tools=["tickets.tickets_search", "tickets.tickets_create", "kb.kb_query"]
    ),
    "acme": TenantPolicy(
        tenant_id="acme",
        allowed_tools=["tickets.tickets_search", "kb.kb_query"]  # No create!
    )
}
```

Notice that "acme" cannot call `tickets.tickets_create`—this policy is enforced before and after the LLM routing step.

**The Orchestration Flow:**

1. Load the tenant's policy
2. Discover tools from all MCP servers
3. Filter tools by allowlist (pre-LLM enforcement)
4. Pass filtered tools to LLM router
5. Validate the router's decision against policy (post-LLM enforcement)
6. Map `tool_id` (e.g., "tickets.tickets_search") to the correct MCP server
7. Invoke the tool via `FastMCPClient`
8. Record the full trace for observability

## Why This Matters: The "Thin" Philosophy

This architecture is deliberately thin in three ways:

### 1. Minimal LLM Surface Area

The model only performs routing—it doesn't have access to raw tool execution, doesn't make policy decisions, and doesn't iterate or plan. This reduces unpredictability, cost, and latency.

### 2. No Custom Protocol

We're using MCP's standard `tools/list` and `tools/call` methods over SSE transport. Any MCP server (built with FastMCP, the official Python SDK, or other implementations) works out of the box.

### 3. Separation of Concerns

- **Policy** lives in code, version-controlled and auditable
- **Routing** is handled by the LLM based on natural language understanding
- **Tool implementation** is encapsulated in MCP servers
- **Observability** is built into the orchestrator via `ToolCallTrace`

This separation means you can:

- Update policies without retraining models
- Swap out LLM providers without changing server code
- Add new MCP servers by just updating the policy allowlist
- Debug exactly what tool was called, with what arguments, and what it returned

## Observability: Trace Everything

Every tool call produces a structured trace:

```python
@dataclass
class ToolCallTrace:
    tenant_id: str
    user_query: str
    tool_id: str
    arguments: Dict[str, Any]
    result: Any
    error: Optional[str]
    timestamp: datetime
```

This makes it trivial to:

- Log all tool usage for compliance
- Debug which tenant called which tool
- Analyze routing accuracy
- Surface errors to users meaningfully

## The MCP Terminology Recap

Let's align this architecture with standard MCP concepts:

**MCP Server**: A backend service (like our tickets or KB servers) that exposes tools (formerly "functions" in older specs). Each server implements the MCP JSON-RPC protocol methods: `initialize`, `tools/list`, `tools/call`, etc.

**MCP Client**: The component that connects to MCP servers, discovers their capabilities, and invokes tools. In our architecture, `FastMCPClient` is the client implementation.

**Tools**: The discrete capabilities exposed by MCP servers. Each tool has a name, description, and input schema (JSON Schema format). Tools are discovered via the `tools/list` method.

**Transport**: The communication mechanism between client and server. We use SSE (Server-Sent Events) for server-to-client messages and HTTP POST for client-to-server requests.

**Session**: A stateful connection between client and server, established via the `initialize` handshake and maintained throughout the interaction.

**Host**: In MCP terminology, the "host" is the application that orchestrates everything—in our case, the `MCPOrchestrator` plus the Streamlit UI. The host is responsible for policy, routing, and presenting results to users.

## Try It Yourself

The full implementation is available at [github.com/adamkicklighter/thin-mcp](https://github.com/adamkicklighter/thin-mcp). To run the demo:

```bash
pip install -r [requirements.txt](http://_vscodecontentref_/0)
streamlit run [app.py](http://_vscodecontentref_/1)
```

Try these prompts:

- "Find open tickets for CVX-12 in last 7 days" → Routes to `tickets.tickets_search`
- "What's the first response for CVX-12 overheating?" → Routes to `kb.kb_query`
- Switch to the "acme" tenant and try "Create a ticket for CVX-12 overheating" → Denied by policy!

## Conclusion: Thin is a Feature, Not a Bug

In a world of increasingly complex AI orchestration frameworks, this thin layer proves that you don't need heavyweight agent platforms to build production-grade multi-server routing. By keeping the LLM's role narrow, enforcing policy in code, and using standard protocols like MCP, you get:

- ✅ **Predictable behavior**: No runaway agent loops
- ✅ **Multi-tenant isolation**: Policy enforced outside the model
- ✅ **Observability**: Every tool call is traced
- ✅ **Extensibility**: Add new MCP servers by updating configuration
- ✅ **Standard compliance**: Works with any MCP server implementation

The future of AI tooling isn't about building monolithic platforms—it's about composing thin, purpose-built layers that each do one thing well. This orchestration pattern is one piece of that puzzle.
