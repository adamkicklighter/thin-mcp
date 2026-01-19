``` mermaid
sequenceDiagram
  autonumber
  participant UI as Streamlit UI
  participant H as Thin Host Orchestrator
  participant P as Tenant Policy
  participant M as MCP Client
  participant TS as Tickets MCP Server
  participant KB as KB MCP Server
  participant L as LLM Router

  Note over UI,H: User interaction and request start
  UI->>H: Submit user_input and tenant_id

  Note over H,P: Governance and tenant scoping
  H->>P: Load tenant policy
  P-->>H: Allowed tools and limits

  Note over H,M: Tool discovery to build allowed catalog
  H->>M: Connect to MCP servers
  M->>TS: list_tools
  TS-->>M: tickets tools
  M->>KB: list_tools
  KB-->>M: kb tools
  M-->>H: Discovered tool catalog
  H->>P: Filter catalog by tenant allowlist
  P-->>H: Allowed tool catalog

  Note over H,L: LLM-based routing decision
  H->>L: Provide user_input and allowed tools
  L-->>H: Route decision (tool_id and args)

  Note over H,P: Enforce policy outside the model
  H->>P: Verify selected tool allowed and within limits
  P-->>H: Approved

  Note over H,M: Tool invocation via SSE
  H->>M: call_tool(tool_id, args)
  alt Tickets tool
    M->>TS: call_tool
    TS-->>M: result
  else KB tool
    M->>KB: call_tool
    KB-->>M: result
  end
  M-->>H: Tool result

  Note over H,UI: Trace and response returned to the UI
  H-->>UI: Result and trace (selected_tool, args, status)
```