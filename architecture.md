``` mermaid
flowchart TB
  %% UI Layer
  subgraph UI["Demo UI (Local)"]
    ST["Streamlit App<br/>User prompt and tenant selector<br/>Shows result and trace"]
  end

  %% Host Layer
  subgraph HOST["Thin Host Orchestrator"]
    ORCH["Orchestrator<br/>Load tenant policy<br/>Discover tools<br/>Route and invoke"]
    POL["Tenant Policy<br/>Allowlist and limits"]
    TRACE["Trace Builder<br/>tool selected<br/>arguments and status"]
  end

  %% LLM Routing Layer
  subgraph LLM["LLM Router"]
    ROUTE["Route Decision<br/>tool_id and args<br/>JSON schema constrained"]
  end

  %% MCP Client and Servers
  subgraph MCP["MCP Tooling"]
    MC["MCP Client<br/>SSE transport"]
    subgraph SRV["MCP Servers"]
      TS["Tickets Server<br/>search and create"]
      KB["Knowledge Base Server<br/>query"]
    end
  end

  %% Primary flow
  ST --> ORCH
  ORCH --> POL
  ORCH --> MC

  MC --> TS
  TS --> MC
  MC --> KB
  KB --> MC

  ORCH --> ROUTE
  ROUTE --> ORCH

  ORCH --> POL
  ORCH --> MC

  MC --> ORCH
  ORCH --> TRACE
  TRACE --> ST

  %% Notes
  classDef note fill:#f6f6f6,stroke:#bbb,color:#111;
  N1["Policy is enforced outside the model.<br/>LLM only chooses from allowed tools"]:::note
  N2["MCP servers represent internal systems<br/>and are swappable"]:::note

  POL -.-> N1
  SRV -.-> N2

```