"""
Repair Mode UI Component.

Allows users to trigger autonomous repair workflows and see results in real-time.
"""

import streamlit as st
import json
from datetime import datetime
from utils.agent_client import AgentClient, MCPClient


def render_repair_mode(agent_client: AgentClient, mcp_client: MCPClient):
    """
    Render the repair mode interface.

    Args:
        agent_client: Client for agent API
        mcp_client: Client for MCP server API
    """
    st.title("🔧 Autonomous Repair System")

    st.markdown("""
    This mode allows you to trigger the AI agent to autonomously diagnose and repair system failures.
    The agent will check container health, read logs, and take corrective actions.
    """)

    # Model selection
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Configuration")

    model_option = st.selectbox(
        "Select Model",
        ["Model A (Llama 3.2 3B - Fast)", "Model B (Llama 3.3 7B - Accurate)", "Compare Both"],
        help="Choose which model to use for the repair workflow"
    )

    # Map display name to model parameter
    if "Model A" in model_option:
        selected_model = "a"
    elif "Model B" in model_option:
        selected_model = "b"
    else:
        selected_model = "compare"

    st.markdown("---")

    # Container status section
    st.subheader("📊 System Status")

    if st.button("🔄 Refresh Status", use_container_width=False):
        st.rerun()

    # Get current container status
    container_status = mcp_client.docker_ps()

    if "error" in container_status:
        st.error(f"Error getting container status: {container_status['error']}")
    else:
        try:
            containers = json.loads(container_status.get("result", "[]"))

            # Display containers in a grid
            cols = st.columns(4)
            for idx, container in enumerate(containers):
                with cols[idx % 4]:
                    status = container.get("status", "unknown")
                    name = container.get("name", "unknown")

                    # Status color
                    if status == "running":
                        status_color = "🟢"
                    elif status in ["exited", "dead"]:
                        status_color = "🔴"
                    elif status in ["restarting", "paused"]:
                        status_color = "🟡"
                    else:
                        status_color = "⚪"

                    st.metric(
                        label=name.replace("ai-monitoring-", ""),
                        value=status,
                        delta=None
                    )
                    st.caption(f"{status_color} {container.get('image', 'N/A')[:20]}")

        except json.JSONDecodeError:
            st.error("Failed to parse container status")

    st.markdown("---")

    # Repair trigger section
    st.subheader("🚀 Trigger Repair")

    if selected_model == "compare":
        repair_button_text = "🔬 Run Repair Comparison (Both Models)"
        repair_help = "This will run the repair workflow with both models sequentially and compare results"
    else:
        model_name = "Model A" if selected_model == "a" else "Model B"
        repair_button_text = f"🚀 Run Repair System ({model_name})"
        repair_help = f"This will trigger the repair workflow using {model_name}"

    if st.button(repair_button_text, type="primary", use_container_width=True, help=repair_help):
        with st.spinner(f"Running repair workflow... This may take 1-3 minutes"):
            if selected_model == "compare":
                result = agent_client.compare_repairs()
            else:
                result = agent_client.trigger_repair(selected_model)

            # Store result in session state
            st.session_state['last_repair_result'] = result
            st.session_state['last_repair_time'] = datetime.now()

    st.markdown("---")

    # Display repair results
    st.subheader("📝 Repair Results")

    if 'last_repair_result' in st.session_state and st.session_state.get('last_repair_result'):
        result = st.session_state['last_repair_result']
        repair_time = st.session_state.get('last_repair_time', datetime.now())

        st.caption(f"Last repair: {repair_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if "error" in result:
            st.error(f"❌ Error: {result['error']}")
        elif "model_a_result" in result:
            # Comparison mode
            st.success("✅ Comparison completed!")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("### Model A Results")
                model_a_result = result.get("model_a_result", {})

                if model_a_result.get("success"):
                    st.success("✅ Success")
                else:
                    st.error("❌ Failed")

                st.metric("Latency", f"{model_a_result.get('latency_seconds', 0):.2f}s")
                st.caption(f"**Final Status:** {model_a_result.get('final_status', 'N/A')}")

                with st.expander("Actions Taken"):
                    for action in model_a_result.get("actions_taken", []):
                        st.text(f"• {action}")

            with col_b:
                st.markdown("### Model B Results")
                model_b_result = result.get("model_b_result", {})

                if model_b_result.get("success"):
                    st.success("✅ Success")
                else:
                    st.error("❌ Failed")

                st.metric("Latency", f"{model_b_result.get('latency_seconds', 0):.2f}s")
                st.caption(f"**Final Status:** {model_b_result.get('final_status', 'N/A')}")

                with st.expander("Actions Taken"):
                    for action in model_b_result.get("actions_taken", []):
                        st.text(f"• {action}")

            # Winner announcement
            winner = result.get("winner")
            reason = result.get("reason", "")

            st.markdown("---")
            st.markdown("### 🏆 Comparison Summary")

            if winner == "a":
                st.info(f"**Winner: Model A** - {reason}")
            elif winner == "b":
                st.info(f"**Winner: Model B** - {reason}")
            else:
                st.info(f"**Result: Tie** - {reason}")

        else:
            # Single model mode
            if result.get("success"):
                st.success("✅ Repair completed successfully!")
            else:
                st.error("❌ Repair failed")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Model", result.get("model_used", "N/A"))

            with col2:
                st.metric("Latency", f"{result.get('latency_seconds', 0):.2f}s")

            with col3:
                containers_restarted = len(result.get("containers_restarted", []))
                st.metric("Containers Restarted", containers_restarted)

            st.markdown(f"**Final Status:** {result.get('final_status', 'N/A')}")

            # Actions taken
            st.markdown("**Actions Taken:**")
            for action in result.get("actions_taken", []):
                st.text(f"• {action}")

            # Raw JSON (for debugging)
            with st.expander("📄 Raw JSON Response"):
                st.json(result)

    else:
        st.info("👆 Click the button above to trigger a repair workflow")

    st.markdown("---")

    # Container logs viewer
    st.subheader("📜 Container Logs")

    container_name = st.selectbox(
        "Select Container",
        [
            "ai-monitoring-target-app",
            "ai-monitoring-chaos-engine",
            "ai-monitoring-mcp-server",
            "ai-monitoring-ai-agent",
            "ai-monitoring-ollama-model-a",
            "ai-monitoring-ollama-model-b"
        ]
    )

    num_lines = st.slider("Number of lines", 10, 200, 50)

    if st.button("📖 Fetch Logs"):
        with st.spinner("Fetching logs..."):
            logs_result = mcp_client.get_container_logs(container_name, num_lines)

            if "error" in logs_result:
                st.error(f"Error: {logs_result['error']}")
            else:
                logs_text = logs_result.get("result", "")
                st.code(logs_text, language="log")
