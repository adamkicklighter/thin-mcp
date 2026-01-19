from __future__ import annotations
import asyncio
import json
import os
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, List

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from host.oai_router import OAIRouter
from host.tenant_policy import TENANTS
from host.types import ToolSpec, ToolCallTrace
from host.orchestrator import MCPOrchestrator, OrchestratorResult

load_dotenv()

# Add logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Streamlit UI code
st.set_page_config(page_title="MCP Orchestrator POC", layout="wide")

st.title("MCP Orchestrator POC (FastMCP + SSE)")
st.caption("Streamlit UI → LLM routes → MCP tools execute → trace displayed")

api_key = os.getenv("OPENAI_API_KEY", "")
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Validate API key exists
if not api_key:
    st.error("❌ OPENAI_API_KEY not found in .env file")
    st.info("Please create a .env file with your OpenAI API key")
    st.stop()

with st.sidebar:
    st.header("Config")
    tenant_id = st.selectbox("Tenant", list(TENANTS.keys()), index=0)
    st.markdown("---")
    st.markdown("**Server Status**")
    st.markdown("Tickets: http://localhost:8000")
    st.markdown("KB: http://localhost:8001")
    st.markdown("---")
    st.markdown("Demo suggestions:")
    st.markdown('- "Find open tickets for CVX-12 in last 7 days"')
    st.markdown('- "What\'s the first response for CVX-12 overheating?"')
    st.markdown("- Try tenant `acme` then ask to create a ticket (should be denied).")
    st.markdown("---")
    st.caption("Check terminal/console for detailed logs")

prompt = st.text_area("User request", height=120, value="Find open tickets for CVX-12 in last 7 days")

colA, colB = st.columns([1, 1], gap="large")

run = colA.button("Run Orchestration", type="primary")

if run:
    client = OpenAI(api_key=api_key)
    router = OAIRouter(client=client, model=model)
    orch = MCPOrchestrator(router=router)
    
    with st.spinner("Routing + invoking MCP tool..."):
        try:
            # Create new event loop for this request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            logger.info("=" * 60)
            logger.info("Starting new orchestration request")
            logger.info("=" * 60)
            
            result = loop.run_until_complete(
                asyncio.wait_for(
                    orch.invoke(tenant_id=tenant_id, user_input=prompt),
                    timeout=60.0
                )
            )
            
            logger.info("=" * 60)
            logger.info("Orchestration completed successfully!")
            logger.info("=" * 60)
            loop.close()
            
        except asyncio.TimeoutError:
            logger.error("Orchestration timed out after 60 seconds")
            st.error("⏱️ Operation timed out after 60 seconds.")
            st.error("Make sure both MCP servers are running:")
            st.code("python servers/tickets_server.py", language="bash")
            st.code("python servers/kb_server.py", language="bash")
            loop.close()
            st.stop()
        except ConnectionError as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            st.error(f"❌ Connection failed: {e}")
            st.error("Make sure both MCP servers are running:")
            st.code("python servers/tickets_server.py", language="bash")
            st.code("python servers/kb_server.py", language="bash")
            loop.close()
            st.stop()
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            st.error(f"❌ Invocation failed: {e}")
            st.info("💡 Check the console/terminal for detailed error logs")
            loop.close()
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