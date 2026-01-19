``` mermaid
flowchart LR
    INPUT[User Request] --> ROUTER[LLM Router]
    TOOLS[Filtered Tool Specs] --> ROUTER
    ROUTER --> SCHEMA[Structured Output<br/>JSON Schema + Strict Mode]
    SCHEMA --> DECISION[RouteDecision<br/>tool_id: str<br/>args: dict]
    DECISION --> SINGLE[Single Tool Call]
    
    style ROUTER fill:#e3f2fd
    style DECISION fill:#c8e6c9
```