``` mermaid
sequenceDiagram
    autonumber
    participant UI
    participant Orchestrator
    participant Policy
    participant FastMCP
    participant Servers
    participant Router
    
    UI->>Orchestrator: invoke(tenant_id, user_input)
    Orchestrator->>Policy: Get tenant policy
    Policy-->>Orchestrator: Allowlist + Limits
    Orchestrator->>FastMCP: discover_tools()
    FastMCP->>Servers: SSE: tools/list
    Servers-->>FastMCP: Tool specs
    FastMCP-->>Orchestrator: All tools
    Orchestrator->>Orchestrator: Filter by allowlist
    Orchestrator->>Router: choose_tool(filtered_tools)
    Router->>Router: LLM structured output
    Router-->>Orchestrator: RouteDecision
    Orchestrator->>Policy: Validate tool_id
    Policy-->>Orchestrator: OK
    Orchestrator->>FastMCP: call_tool(tool_name, args)
    FastMCP->>Servers: SSE: tools/call
    Servers-->>FastMCP: Result
    FastMCP-->>Orchestrator: Result
    Orchestrator->>Orchestrator: Create trace
    Orchestrator-->>UI: OrchestratorResult(tool, trace, result)
```