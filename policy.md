``` mermaid
sequenceDiagram
    participant O as Orchestrator
    participant P as TenantPolicy
    participant M as MCP Servers
    participant R as LLM Router

    O->>M: Discover ALL tools
    M-->>O: Full tool catalog
    O->>P: Get tenant allowlist
    P-->>O: Allowed tool IDs
    O->>O: Filter: only allowed tools
    O->>R: Route using filtered tools
    Note over R: LLM never sees<br/>forbidden tools
```