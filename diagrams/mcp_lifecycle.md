``` mermaid
sequenceDiagram
  autonumber
  participant Op as Operator / Deploy
  participant API as FastAPI Host
  participant Reg as Tool Registry + Index
  participant Pol as Tenant Policy Store
  participant R as Router
  participant Ex as Executor
  participant CM as SSE Connection Manager
  participant S1 as MCP Server A
  participant S2 as MCP Server B
  participant Obs as Logs / Metrics

  %% --- Startup lifecycle ---
  Op->>API: Start host
  API->>CM: Initialize SSE clients (per server)
  par Connect servers
    CM->>S1: Open SSE stream
    CM->>S2: Open SSE stream
  end
  par Load manifests
    API->>S1: Fetch manifest (tools + schemas)
    API->>S2: Fetch manifest (tools + schemas)
  end
  API->>Reg: Merge tools + build indexes (tag/keyword/server)
  API->>Obs: Log: tool_count, servers_connected

  %% --- Steady-state request handling ---
  Note over API,Obs: Steady-state: /invoke handles tenant-scoped routing + execution

  Op->>API: POST /invoke {tenant_id, input}
  API->>Pol: Resolve tenant policy (allowlist + limits)
  Pol-->>API: allowed_tools/tags + budgets

  API->>Reg: Get tenant-filtered tool view
  Reg-->>API: eligible tools (subset) + indexes

  API->>R: Route(input, eligible_tools)
  R-->>API: selected_tool_id + inferred_args

  API->>Ex: Execute(selected_tool_id, args, tenant_ctx)
  Ex->>Obs: Log: trace_id, tenant_id, tool_id (start)
  Ex->>CM: Invoke tool (request_id, tool_name, args, tenant auth)

  %% SSE correlation pattern
  CM->>S1: POST invoke (request_id, tool, args)
  S1-->>CM: SSE event {request_id, ok, result}
  CM-->>Ex: Resolve Future(request_id) -> payload

  Ex->>Obs: Log: trace_id, tool latency, success/failure
  Ex-->>API: result + tool_call metadata
  API-->>Op: 200 OK {trace_id, result}

  %% --- Refresh / reconnect lifecycle ---
  Note over CM,Reg: Background: handle reconnects and periodic manifest refresh

  alt Server disconnects or errors
    CM-->>Obs: Log: SSE disconnect + backoff
    CM->>S1: Reconnect SSE stream (backoff)
    API->>S1: Refresh manifest after reconnect
    API->>Reg: Update tool catalog + rebuild indexes
    API->>Obs: Log: refresh complete
  else Periodic refresh window
    API->>S2: Refresh manifest (TTL)
    API->>Reg: Merge updates + rebuild indexes
    API->>Obs: Log: refresh complete
  end
```