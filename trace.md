``` mermaid
classDiagram
    class ToolCallTrace {
        +str tool_id
        +dict args
        +bool ok
        +Optional[str] error
        +str result_preview
    }
    
    class OrchestratorResult {
        +str selected_tool
        +List[ToolCallTrace] trace
        +Any result
    }
    
    OrchestratorResult --> ToolCallTrace: contains
    
    note for ToolCallTrace "Captures every tool invocation\nfor debugging and audit"
```