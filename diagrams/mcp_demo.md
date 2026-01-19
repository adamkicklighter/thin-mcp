``` mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant H as MCP Host
  participant T as Tenant Policy
  participant S as Tool Server

  U->>H: Natural language request
  H->>T: Check tenant permissions
  T-->>H: Allowed tools + limits
  H->>S: Invoke selected tool (SSE)
  S-->>H: Tool result
  H-->>U: Response + trace_id
```