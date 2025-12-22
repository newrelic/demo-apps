"""
AI Monitoring Demo - Streamlit UI

Main application file that provides navigation between different modes:
- Repair Mode: Autonomous system repair
- Chat Mode: Free-form conversation for hallucination detection
- Model Comparison: Performance metrics and A/B testing
"""

import os
import streamlit as st
from utils.agent_client import AgentClient, MCPClient
from components.repair_mode import render_repair_mode
from components.chat_mode import render_chat_mode
from components.model_comparison import render_model_comparison

# Page configuration
st.set_page_config(
    page_title="AI Monitoring Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize clients
AGENT_URL = os.getenv("AGENT_URL", "http://ai-agent:8001")
MCP_URL = os.getenv("MCP_URL", "http://mcp-server:8002")

agent_client = AgentClient(AGENT_URL)
mcp_client = MCPClient(MCP_URL)

# Sidebar
with st.sidebar:
    st.title("🤖 AI Monitoring Demo")

    st.markdown("---")

    # Mode selection
    mode = st.radio(
        "Select Mode",
        ["🔧 Repair System", "💬 Chat Assistant", "📊 Model Comparison"],
        help="Choose which interface to display"
    )

    st.markdown("---")

    # System information
    st.subheader("System Info")

    # Check agent health
    health = agent_client.health_check()

    if "error" not in health:
        st.success("✅ Agent: Online")
        uptime = health.get("uptime_seconds", 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        st.caption(f"Uptime: {hours}h {minutes}m")
    else:
        st.error("❌ Agent: Offline")

    st.markdown("---")

    # Model information
    st.subheader("Models")

    st.caption("**Model A (Fast)**")
    st.text("Llama 3.2 3B")
    st.caption("~1-2s response time")

    st.caption("**Model B (Accurate)**")
    st.text("Llama 3.3 7B")
    st.caption("~3-5s response time")

    st.markdown("---")

    # Quick stats
    metrics = agent_client.get_metrics()

    if "error" not in metrics:
        model_a_total = metrics.get("model_a", {}).get("total_requests", 0)
        model_b_total = metrics.get("model_b", {}).get("total_requests", 0)

        st.subheader("Quick Stats")
        st.metric("Model A Requests", model_a_total)
        st.metric("Model B Requests", model_b_total)

    st.markdown("---")

    # Links
    st.subheader("Resources")

    st.markdown("""
    - [Agent API]({AGENT_URL})
    - [MCP Server]({MCP_URL})
    - [Locust UI](http://localhost:8089)
    - [Target App](http://localhost:8000)
    """.format(AGENT_URL=AGENT_URL, MCP_URL=MCP_URL))

    st.markdown("---")

    # Footer
    st.caption("🔬 Built for New Relic AI Monitoring Demo")
    st.caption("Showcasing autonomous repair, model comparison, and hallucination detection")

# Main content area
if mode == "🔧 Repair System":
    render_repair_mode(agent_client, mcp_client)

elif mode == "💬 Chat Assistant":
    render_chat_mode(agent_client)

elif mode == "📊 Model Comparison":
    render_model_comparison(agent_client)

# Footer
st.markdown("---")

footer_cols = st.columns(3)

with footer_cols[0]:
    st.caption("🤖 Powered by PydanticAI + Ollama")

with footer_cols[1]:
    st.caption("🐳 Running in Docker Compose")

with footer_cols[2]:
    st.caption("📊 Ready for New Relic instrumentation")
