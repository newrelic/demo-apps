"""
Model Comparison Dashboard Component.

Displays side-by-side metrics and performance comparison for Model A vs Model B.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.agent_client import AgentClient


def render_model_comparison(agent_client: AgentClient):
    """
    Render the model comparison dashboard.

    Args:
        agent_client: Client for agent API
    """
    st.title("📊 Model Comparison Dashboard")

    st.markdown("""
    Compare the performance of Model A (Llama 3.2 3B) vs Model B (Llama 3.3 7B).
    This dashboard showcases New Relic's model comparison capabilities.
    """)

    # Refresh button
    if st.button("🔄 Refresh Metrics"):
        st.rerun()

    # Get metrics
    metrics = agent_client.get_metrics()

    if "error" in metrics:
        st.error(f"Error loading metrics: {metrics['error']}")
        return

    model_a_metrics = metrics.get("model_a", {})
    model_b_metrics = metrics.get("model_b", {})

    # Overview metrics
    st.subheader("📈 Performance Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Model A Total Requests",
            model_a_metrics.get("total_requests", 0)
        )

    with col2:
        success_rate_a = model_a_metrics.get("success_rate", 0) * 100
        st.metric(
            "Model A Success Rate",
            f"{success_rate_a:.1f}%"
        )

    with col3:
        st.metric(
            "Model B Total Requests",
            model_b_metrics.get("total_requests", 0)
        )

    with col4:
        success_rate_b = model_b_metrics.get("success_rate", 0) * 100
        st.metric(
            "Model B Success Rate",
            f"{success_rate_b:.1f}%"
        )

    st.markdown("---")

    # Side-by-side comparison
    st.subheader("🔬 Detailed Comparison")

    comp_col1, comp_col2 = st.columns(2)

    with comp_col1:
        st.markdown("### Model A (Fast Baseline)")
        st.markdown(f"**Model:** {model_a_metrics.get('name', 'N/A')}")

        st.metric("Total Requests", model_a_metrics.get("total_requests", 0))
        st.metric("Successful", model_a_metrics.get("successful_requests", 0))
        st.metric("Failed", model_a_metrics.get("failed_requests", 0))
        st.metric("Avg Latency", f"{model_a_metrics.get('avg_latency_seconds', 0):.2f}s")

    with comp_col2:
        st.markdown("### Model B (Premium)")
        st.markdown(f"**Model:** {model_b_metrics.get('name', 'N/A')}")

        st.metric("Total Requests", model_b_metrics.get("total_requests", 0))
        st.metric("Successful", model_b_metrics.get("successful_requests", 0))
        st.metric("Failed", model_b_metrics.get("failed_requests", 0))
        st.metric("Avg Latency", f"{model_b_metrics.get('avg_latency_seconds', 0):.2f}s")

    st.markdown("---")

    # Latency comparison chart
    st.subheader("⚡ Latency Comparison")

    fig_latency = go.Figure()

    fig_latency.add_trace(go.Bar(
        name='Model A',
        x=['Average Latency'],
        y=[model_a_metrics.get("avg_latency_seconds", 0)],
        marker_color='lightblue'
    ))

    fig_latency.add_trace(go.Bar(
        name='Model B',
        x=['Average Latency'],
        y=[model_b_metrics.get("avg_latency_seconds", 0)],
        marker_color='lightcoral'
    ))

    fig_latency.update_layout(
        title="Average Response Latency (seconds)",
        yaxis_title="Seconds",
        barmode='group',
        height=400
    )

    st.plotly_chart(fig_latency, use_container_width=True)

    # Success rate comparison
    st.subheader("✅ Success Rate Comparison")

    fig_success = go.Figure()

    fig_success.add_trace(go.Bar(
        name='Model A',
        x=['Success Rate'],
        y=[success_rate_a],
        marker_color='lightblue',
        text=[f"{success_rate_a:.1f}%"],
        textposition='auto'
    ))

    fig_success.add_trace(go.Bar(
        name='Model B',
        x=['Success Rate'],
        y=[success_rate_b],
        marker_color='lightcoral',
        text=[f"{success_rate_b:.1f}%"],
        textposition='auto'
    ))

    fig_success.update_layout(
        title="Success Rate Percentage",
        yaxis_title="Percentage",
        yaxis_range=[0, 100],
        barmode='group',
        height=400
    )

    st.plotly_chart(fig_success, use_container_width=True)

    # Comparison table
    st.subheader("📋 Metrics Table")

    comparison_data = {
        "Metric": [
            "Model Name",
            "Total Requests",
            "Successful Requests",
            "Failed Requests",
            "Success Rate",
            "Avg Latency (s)"
        ],
        "Model A": [
            model_a_metrics.get("name", "N/A"),
            model_a_metrics.get("total_requests", 0),
            model_a_metrics.get("successful_requests", 0),
            model_a_metrics.get("failed_requests", 0),
            f"{success_rate_a:.1f}%",
            f"{model_a_metrics.get('avg_latency_seconds', 0):.2f}"
        ],
        "Model B": [
            model_b_metrics.get("name", "N/A"),
            model_b_metrics.get("total_requests", 0),
            model_b_metrics.get("successful_requests", 0),
            model_b_metrics.get("failed_requests", 0),
            f"{success_rate_b:.1f}%",
            f"{model_b_metrics.get('avg_latency_seconds', 0):.2f}"
        ]
    }

    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Analysis and insights
    st.subheader("🎯 Insights")

    total_a = model_a_metrics.get("total_requests", 0)
    total_b = model_b_metrics.get("total_requests", 0)

    if total_a > 0 or total_b > 0:
        latency_a = model_a_metrics.get("avg_latency_seconds", 0)
        latency_b = model_b_metrics.get("avg_latency_seconds", 0)

        col_insight1, col_insight2 = st.columns(2)

        with col_insight1:
            st.markdown("### ⚡ Speed")
            if latency_a < latency_b:
                speed_advantage = ((latency_b - latency_a) / latency_b * 100) if latency_b > 0 else 0
                st.success(f"Model A is **{speed_advantage:.1f}% faster** than Model B")
            elif latency_b < latency_a:
                speed_advantage = ((latency_a - latency_b) / latency_a * 100) if latency_a > 0 else 0
                st.success(f"Model B is **{speed_advantage:.1f}% faster** than Model A")
            else:
                st.info("Both models have similar latency")

        with col_insight2:
            st.markdown("### 🎯 Accuracy")
            if success_rate_a > success_rate_b:
                st.success(f"Model A has a **{success_rate_a - success_rate_b:.1f}%** higher success rate")
            elif success_rate_b > success_rate_a:
                st.success(f"Model B has a **{success_rate_b - success_rate_a:.1f}%** higher success rate")
            else:
                st.info("Both models have similar success rates")

        st.markdown("---")

        st.markdown("### 💡 Recommendation")

        if total_a >= 3 and total_b >= 3:  # Only make recommendations with sufficient data
            # Cost vs. performance analysis
            if success_rate_a >= 95 and success_rate_b >= 95:
                # Both are highly successful
                if latency_a < latency_b:
                    st.info("✅ **Use Model A** for cost-effective, high-performance repairs with fast response times.")
                else:
                    st.info("✅ **Use Model B** for maximum reliability, despite higher latency.")
            elif success_rate_a > success_rate_b:
                st.info("✅ **Use Model A** - Better success rate and faster responses.")
            elif success_rate_b > success_rate_a:
                st.info("✅ **Use Model B** - Higher success rate justifies the additional latency.")
            else:
                st.info("⚖️ **Both models perform similarly** - Choose based on cost and latency requirements.")
        else:
            st.warning("⏳ More data needed for accurate recommendations. Run more repair workflows.")

    else:
        st.info("📊 No metrics available yet. Run some repair workflows or chat interactions to see data.")

    # Export section
    st.markdown("---")
    st.subheader("📥 Export Data")

    st.markdown("""
    In a production deployment, this data would be automatically exported to New Relic
    for comprehensive analysis and alerting.
    """)

    if st.button("📊 Export to JSON"):
        st.download_button(
            label="Download Metrics JSON",
            data=str(metrics),
            file_name="model_comparison_metrics.json",
            mime="application/json"
        )

    # New Relic integration info
    with st.expander("ℹ️ About New Relic Model Comparison"):
        st.markdown("""
        ### New Relic AI Monitoring Features

        When instrumented with New Relic, this dashboard data would include:

        **Performance Metrics:**
        - Token usage per model
        - Cost per request (based on token usage)
        - Latency distribution (P50, P95, P99)
        - Error rates and types

        **Quality Metrics:**
        - Hallucination detection scores
        - Response quality ratings
        - User satisfaction metrics
        - Conversation success rates

        **Comparison Features:**
        - A/B test statistical significance
        - Cost-benefit analysis
        - Automated model selection recommendations
        - Performance trend analysis over time

        **Alerting:**
        - Anomaly detection for sudden performance changes
        - Threshold alerts for latency or error rates
        - Cost overrun warnings
        - Model drift detection
        """)
