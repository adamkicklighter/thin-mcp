``` mermaid
stateDiagram-v2
    [*] --> Disconnected
    Disconnected --> Connecting: connect()
    Connecting --> WaitingForEndpoint: Start SSE stream
    WaitingForEndpoint --> WaitingForInit: Receive /messages endpoint
    WaitingForInit --> Connected: Send & receive initialize
    Connected --> ToolsList: list_tools()
    Connected --> ToolsCall: call_tool()
    ToolsList --> Connected: Return tools
    ToolsCall --> Connected: Return result
    Connected --> [*]: close()
    
    note right of Connected
        Session ID maintained
        Async queue for responses
        Concurrent request/response
    end note
```