``` mermaid
flowchart LR
  U["User / App"] -->|Request| API["FastAPI MCP Host"]

  subgraph HOST["MCP Host (Thin Orchestrator)"]
    API --> R["Router<br/>Selects Tool"]
    R --> P["Policy Gate<br/>Tenant Rules"]
    P --> X["Executor<br/>Calls Tool"]
  end

  subgraph GOV["Governance"]
    T["Tenant Policies<br/>Allowlists & Limits"]
  end

  P --> T

  subgraph TOOLS["MCP Tool Servers"]
    S1["Ticketing"]
    S2["Knowledge Base"]
    S3["Email / Notifications"]
  end

  X <-->|SSE| S1
  X <-->|SSE| S2
  X <-->|SSE| S3
```