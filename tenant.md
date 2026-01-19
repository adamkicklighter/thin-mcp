``` mermaid
graph LR
    subgraph "Tenant: ACME"
        A_POL[Policy:<br/>tickets_search<br/>kb_query]
    end
    
    subgraph "Tenant: GLOBEX"
        G_POL[Policy:<br/>tickets_search<br/>tickets_create<br/>kb_query]
    end
    
    subgraph "Shared Tool Catalog"
        T1[tickets_search]
        T2[tickets_create]
        T3[kb_query]
    end
    
    A_POL -.->|Allowed| T1
    A_POL -.->|Allowed| T3
    A_POL -.->|Denied| T2
    
    G_POL -.->|Allowed| T1
    G_POL -.->|Allowed| T2
    G_POL -.->|Allowed| T3
    
    style T2 fill:#ffcdd2
```