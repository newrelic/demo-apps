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

    st.caption("**Model A (llama3.2:1b - Fast & Reliable)**")
    st.text("Meta's small model")
    st.caption("~0.5-1s response time")

    st.caption("**Model B (qwen2.5:0.5b - Ultra Lightweight)**")
    st.text("Alibaba's tiny model")
    st.caption("~0.3-0.5s response time")

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

    # Load Testing section
    with st.expander("🔬 Load Testing", expanded=False):
        st.caption("Generate passive load for New Relic demo data")

        # Check current status
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Check Status", use_container_width=True):
                with st.spinner("Checking..."):
                    stats = mcp_client.get_load_test_stats()
                    st.session_state['load_test_stats'] = stats

        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        # Display current status
        if 'load_test_stats' in st.session_state:
            stats = st.session_state['load_test_stats']

            if "error" in stats:
                st.error(f"⚠️ {stats['error']}")
            else:
                status = stats.get("status", "unknown")

                if status == "running":
                    st.success("✅ Load test running")

                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric("Requests", stats.get("total_requests", 0))
                        st.metric("Users", stats.get("user_count", 0))

                    with metric_col2:
                        avg_time = stats.get("avg_response_time", 0)
                        st.metric("Avg Time", f"{avg_time:.0f}ms")
                        rps = stats.get("requests_per_second", 0)
                        st.metric("RPS", f"{rps:.1f}")

                    st.caption("ℹ️ ~10% error rate expected (error-causing prompts)")

                    # Stop button
                    if st.button("⏹️ Stop Test", use_container_width=True, type="secondary"):
                        with st.spinner("Stopping..."):
                            result = mcp_client.stop_load_test()
                            if "error" in result:
                                st.error(f"❌ {result['error']}")
                            else:
                                st.success("Stopped successfully")
                                del st.session_state['load_test_stats']
                                st.rerun()

                elif status == "stopped":
                    st.info("⏸️ No test running")
                else:
                    st.warning(f"Status: {status}")

        st.markdown("---")
        st.markdown("**Start New Test:**")

        # Configuration
        config_col1, config_col2 = st.columns(2)
        with config_col1:
            users = st.number_input("Users", min_value=1, max_value=50, value=10, help="Concurrent users")
        with config_col2:
            duration_min = st.number_input("Duration (min)", min_value=1, max_value=120, value=30, help="Test duration")

        # Start button
        if st.button("🚀 Start Load Test", use_container_width=True, type="primary"):
            with st.spinner(f"Starting {users} users for {duration_min}min..."):
                result = mcp_client.start_load_test(
                    users=users,
                    spawn_rate=2,
                    duration=duration_min * 60
                )

                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    st.success(f"✅ Started: {users} users, {duration_min}min")
                    st.info("💡 View details at http://localhost:8089")
                    st.rerun()

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
