``` mermaid
flowchart TB
  U["Caller<br/>UI / CLI / App"] -->|HTTP| API["FastAPI<br/>/invoke /tools /health"]

  subgraph Host["MCP Host - POC"]
    API --> Ctx["Tenant Context Resolver<br/>tenant_id, limits, allowlist"]
    Ctx --> R["Router - Rules + Index"]
    R -->|tool_id + args| X["Executor"]

    subgraph RouterInternals["Router Internals"]
      R --> Sig["Signal Extractor<br/>keywords, entities, time hints"]
      R --> Idx["Capability Index<br/>tag->tools, keyword->tools"]
      R --> Sc["Scorer<br/>rank candidates"]
      R --> PolF["Policy Filter<br/>tenant allowlist"]
      Sig --> Idx --> Sc --> PolF
    end

    subgraph Runtime["Runtime"]
      X --> Val["Args Validation<br/>Pydantic / JSONSchema"]
      X --> Bud["Budget Gate<br/>max calls, timeouts"]
      X --> Log["Trace Logger<br/>trace_id, tenant_id, tool_id"]
      Val --> Bud --> Log
    end
  end

  subgraph SSE["SSE Layer"]
    CM["Connection Manager<br/>persistent per server"]
    Corr["Correlation Map<br/>request_id->Future"]
    CM --> Corr
  end

  X --> CM
  CM <-->|SSE| S1["MCP Server A<br/>tools..."]
  CM <-->|SSE| S2["MCP Server B<br/>tools..."]
  CM <-->|SSE| S3["MCP Server C<br/>tools..."]
```