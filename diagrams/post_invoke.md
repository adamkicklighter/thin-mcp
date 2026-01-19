``` mermaid
sequenceDiagram
  autonumber
  participant U as Caller
  participant API as FastAPI /invoke
  participant Ctx as Tenant Context Resolver
  participant Reg as Tool Registry + Index
  participant R as Router
  participant X as Executor
  participant CM as SSE Conn Manager
  participant S as MCP Server

  U->>API: POST /invoke {tenant_id, input}
  API->>Ctx: load policy/limits for tenant
  Ctx-->>API: allowlist + budgets
  API->>Reg: get tools (cached manifest)
  Reg-->>API: tool records + indexes
  API->>R: route(input, tenant_allowlist, indexes)
  R-->>API: selected tool_id + args
  API->>X: execute(tool_id, args, tenant_ctx)
  X->>CM: invoke(tool_id, args, request_id)
  CM->>S: SSE request (request_id)
  S-->>CM: SSE response (request_id)
  CM-->>X: tool_result
  X-->>API: result + trace_id + tool_calls
  API-->>U: 200 OK
```