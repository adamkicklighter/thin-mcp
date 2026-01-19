# Host Architecture - Mermaid Diagram

## Overview
The host layer implements a **thin orchestrator pattern** where policy is enforced outside the LLM, and the model acts purely as a router (not an agent). This architecture ensures tenant isolation, tool governance, and observability.

## Architecture Diagram

```mermaid
graph TB
    subgraph "External"
        UI[Streamlit UI<br/>User Input + Tenant Selection]
    end

    subgraph "Host Layer - Novel Components"
        ORCH[MCPOrchestrator<br/>Main Coordination Logic]
        
        subgraph "Policy Enforcement"
            TPOL[TenantPolicy<br/>Allowlist + Limits]
            POL_CHECK{Policy Filter<br/>Allowed Tools Only}
        end
        
        subgraph "LLM Router (Non-Agentic)"
            ROUTER[OAIRouter<br/>OpenAI Structured Outputs]
            DECISION[RouteDecision<br/>tool_id + args]
        end
        
        subgraph "MCP Client Layer"
            FASTMCP[FastMCPClient<br/>SSE Transport]
            SSE[SSE Stream Handler<br/>Async Queue Pattern]
            SESSION[Session Management<br/>Initialize & Lifecycle]
        end
        
        subgraph "Observability"
            TRACE[ToolCallTrace<br/>Record: tool_id, args, result, error]
        end
    end

    subgraph "MCP Servers (External Services)"
        TICKETS[Tickets Server<br/>:8000]
        KB[KB Server<br/>:8001]
    end

    %% Flow
    UI -->|1. User Request + tenant_id| ORCH
    ORCH -->|2. Load Policy| TPOL
    ORCH -->|3. Discover Tools| FASTMCP
    FASTMCP -->|SSE: tools/list| TICKETS
    FASTMCP -->|SSE: tools/list| KB
    TICKETS -->|Tool Specs| FASTMCP
    KB -->|Tool Specs| FASTMCP
    FASTMCP -->|4. All Tools| ORCH
    ORCH -->|5. Filter by Policy| POL_CHECK
    POL_CHECK -->|Allowed Tools Only| ROUTER
    ROUTER -->|6. LLM Chooses| DECISION
    DECISION -->|7. Validate Policy| POL_CHECK
    POL_CHECK -->|8. If Allowed| FASTMCP
    FASTMCP -->|SSE: tools/call| TICKETS
    FASTMCP -->|SSE: tools/call| KB
    TICKETS -->|Result| FASTMCP
    KB -->|Result| FASTMCP
    FASTMCP -->|9. Result| ORCH
    ORCH -->|10. Record| TRACE
    TRACE -->|11. Result + Trace| UI

    %% Styling
    classDef novel fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    classDef policy fill:#fff3cd,stroke:#ffc107,stroke-width:2px
    classDef llm fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef mcp fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    
    class ORCH,FASTMCP,SESSION,SSE novel
    class TPOL,POL_CHECK policy
    class ROUTER,DECISION llm
    class TRACE mcp
```