from __future__ import annotations
import asyncio
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from host.oai_router import OAIRouter
from host.orchestrator import MCPOrchestrator
from host.tenant_policy import TENANTS

load_dotenv()

st.set_page_config(page_title="MCP Orchestrator POC", layout="wide")

st.title("MCP Orchestrator POC (Local)")
st.caption("Streamlit UI → LLM routes → MCP tools execute → trace displayed")

api_key = os.getenv("OPENAI_API_KEY", "")
model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

with st.sidebar:
    st.header("Config")
    tenant_id = st.selectbox("Tenant", list(TENANTS.keys()), index=0)
    st.text_input("OpenAI model", value=model, key="model_name")
    st.text_input("OPENAI_API_KEY", value=api_key, type="password", key="api_key")
    st.markdown("---")
    st.markdown("Demo suggestions:")
    st.markdown("- “Find open tickets for CVX-12 in last 7 days”")
    st.markdown("- “What’s the first response for CVX-12 overheating?”")
    st.markdown("- Try tenant `acme` then ask to create a ticket (should be denied).")

prompt = st.text_area("User request", height=120, value="Find open tickets for CVX-12 in last 7 days")

colA, colB = st.columns([1, 1], gap="large")

run = colA.button("Run Orchestration", type="primary")

if run:
    if not st.session_state["api_key"]:
        st.error("Missing OPENAI_API_KEY")
        st.stop()

    client = OpenAI(api_key=st.session_state["api_key"])
    router = OAIRouter(client=client, model=st.session_state["model_name"])
    orch = MCPOrchestrator(router=router)

    with st.spinner("Routing + invoking MCP tool..."):
        try:
            result = asyncio.run(orch.invoke(tenant_id=tenant_id, user_input=prompt))
        except Exception as e:
            st.error(f"Invocation failed: {e}")
            st.stop()

    colA.subheader("Result")
    colA.write(result.result)

    colB.subheader("Trace")
    colB.json(
        {
            "tenant_id": tenant_id,
            "selected_tool": result.selected_tool,
            "tool_calls": [t.__dict__ for t in result.trace],
        }
    )