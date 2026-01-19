# MCP Orchestrator POC (Local)

This POC demonstrates:
- Streamlit UI for live demo
- Thin host/orchestrator that uses an OpenAI model to choose the right tool
- MCP servers (tickets + kb) running locally
- Multi-tenant allowlists and a visible trace of tool calls

## Setup
1) Create venv and install deps
   pip install -r requirements.txt

2) Create `.env` from `.env.example` and set OPENAI_API_KEY

## Run the demo
streamlit run app_streamlit.py

## Suggested demo prompts
- "Find open tickets for CVX-12 in last 7 days"
- "What's the first response for CVX-12 overheating?"
- Switch tenant to `acme` and ask "Create a ticket for CVX-12 overheating"
  (should be denied by allowlist)