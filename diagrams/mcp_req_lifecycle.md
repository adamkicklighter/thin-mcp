``` mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant API as MCP Host API
  participant MW as Tenant Middleware
  participant RT as Router
  participant POL as Policy Gate
  participant EX as Executor
  participant CM as SSE Conn Manager
  participant S as MCP Server

  U->>API: POST /invoke
  API->>MW: authenticate + tenant context
  MW->>RT: route(input)
  RT-->>MW: tool + args
  MW->>EX: execute
  EX->>POL: policy + quotas
  POL-->>EX: approved
  EX->>CM: invoke(tool, request_id)
  CM->>S: SSE request
  S-->>CM: SSE response (request_id)
  CM-->>EX: result
  EX-->>API: response + trace_id
  API-->>U: 200 OK
```