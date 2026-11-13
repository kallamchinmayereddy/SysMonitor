"""
SysMonitor Dashboard - Alerts & System Health Page
Displays active alerts, full historical alert log with acknowledgment controls,
threshold configuration review, and the explainable heuristic System Health Score.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from analytics.health_score import HealthScoreCalculator
from collector.monitoring_engine import MonitoringEngine
from database.db_manager import DatabaseManager
from dashboard.styles import get_plotly_layout, render_metric_card


def render_alerts_page():
    """Renders the alerts management and system health diagnostic view."""
    engine = MonitoringEngine.get_instance()
    db = DatabaseManager.get_instance()
    health_calc = HealthScoreCalculator()

    metrics = engine.get_latest_metrics()
    if not metrics:
        metrics = engine.trigger_single_collection()

    st.title("System Health & Alert Center")
    st.caption("Threshold breach monitoring, statistical anomaly logs, and heuristic system health scoring.")

    # Educational Guide Expander
    with st.expander("💡 How Alerts, Health Scoring & Anomaly Detection Work", expanded=False):
        st.markdown(
            """
**Understanding System Health Diagnostics, Threshold Alerts & Anomaly Detection:**

- **Explainable System Health Score (0–100)**:
  - An intelligent heuristic index starting at 100 and subtracting weighted penalties for constrained resources (CPU load, memory pressure, and low disk space).
  - 🟢 **90–100 (Optimal)**: Computer is running at peak responsiveness with abundant headroom.
  - 🔵 **75–89 (Good)**: Normal day-to-day computing load.
  - 🟡 **50–74 (Degraded)**: At least one subsystem is heavily loaded; background apps or multitasking may feel sluggish.
  - 🔴 **Below 50 (Critical)**: Severe resource contention; requires closing heavy processes or freeing disk space.
- **Explainable Diagnostics**:
  - Transparently lists the exact penalty points deducted per resource, observations made, and practical troubleshooting steps to restore optimal performance.
- **Dual-Layer Alert Engine**:
  - **1. Static Thresholds**: Triggers when metrics cross configured ceilings (e.g., CPU ≥ 80% Warning, CPU ≥ 90% Critical).
  - **2. Statistical Anomaly Detection ($Z \\ge 2.5\\sigma$)**: Computes a dynamic rolling baseline (mean $\\mu$ and standard deviation $\\sigma$). Spikes exceeding $2.5\\sigma$ above recent history trigger intelligent anomaly notifications before reaching catastrophic thresholds.
- **Alert Deduplication & Acknowledgment**:
  - A 60-second cooldown window prevents duplicate alerts from spamming the log during sustained load.
  - Use the acknowledgment buttons to mark reviewed alerts as resolved.
            """
        )

    # 1. System Health Score & Diagnostics Section
    health = health_calc.calculate(
        cpu_percent=metrics.get("cpu_percent"),
        memory_percent=metrics.get("memory_percent"),
        disk_percent=metrics.get("disk_percent"),
    )

    h_col1, h_col2 = st.columns([1, 2])

    with h_col1:
        # Gauge chart for health score
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health["score"],
            title={"text": f"Health Score: {health['category']}", "font": {"color": "#c9d1d9", "size": 16}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                "bar": {"color": health["status_color"]},
                "bgcolor": "#161b22",
                "steps": [
                    {"range": [0, 50], "color": "rgba(248, 81, 73, 0.2)"},
                    {"range": [50, 75], "color": "rgba(210, 153, 34, 0.2)"},
                    {"range": [75, 90], "color": "rgba(99, 110, 250, 0.2)"},
                    {"range": [90, 100], "color": "rgba(63, 185, 80, 0.2)"},
                ],
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#0d1117",
            height=260,
            margin=dict(l=20, r=20, t=30, b=20),
            font=dict(color="#c9d1d9"),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with h_col2:
        st.subheader("Diagnostic Evaluation & Troubleshooting")
        penalties = health["penalties"]
        st.markdown(
            f"**Resource Penalty Breakdown:** "
            f"CPU Penalty: `-{penalties['cpu']:.1f}` | "
            f"RAM Penalty: `-{penalties['memory']:.1f}` | "
            f"Disk Penalty: `-{penalties['disk']:.1f}`"
        )

        st.markdown("**Identified Observations:**")
        for r in health["reasons"]:
            st.markdown(f"- {r}")

        st.markdown("**Recommended Actions:**")
        for rec in health["recommendations"]:
            st.markdown(f"- 💡 {rec}")

        st.caption("*Note: The System Health Score is an explainable heuristic performance index, not a hardware fault diagnosis.*")

    st.markdown("---")

    # 2. Alert Actions & Controls
    st.subheader("Alert Events & History")

    c_ack, c_exp = st.columns([2, 1])
    with c_ack:
        if st.button("✅ Acknowledge All Pending Alerts", help="Mark all currently unacknowledged warning and critical alert events as reviewed."):
            count = db.acknowledge_all_alerts()
            st.success(f"Acknowledged {count} alert(s).")
            st.rerun()

    with c_exp:
        alerts_csv = db.export_alerts_csv()
        if alerts_csv:
            st.download_button(
                "📥 Export Alerts CSV",
                data=alerts_csv,
                file_name="sysmonitor_alerts.csv",
                mime="text/csv",
                help="Download full historical log of system threshold breaches and anomaly events as a CSV file.",
            )

    # 3. Alerts Table
    filter_unack = st.checkbox("Show only unacknowledged alerts", value=False, help="Filter out alerts that have already been acknowledged.")
    alerts_df = db.get_alerts(unacknowledged_only=filter_unack, limit=100)

    if not alerts_df.empty:
        # Acknowledgment interactive button for top unacknowledged
        display_rows = []
        for _, row in alerts_df.iterrows():
            display_rows.append({
                "ID": row["id"],
                "Severity": row["severity"],
                "Resource": row["resource_type"],
                "Message": row["message"],
                "Observed": f"{row['observed_value']:.1f}",
                "Threshold": f"{row['threshold_value']:.1f}",
                "Triggered Time": row.get("datetime", row["timestamp"]),
                "Status": "✅ Acknowledged" if row["acknowledged"] else "⚠️ Active",
            })
        st.dataframe(pd.DataFrame(display_rows), hide_index=True, use_container_width=True)

        # Single alert acknowledgment selector
        unack_ids = alerts_df[alerts_df["acknowledged"] == 0]["id"].tolist()
        if unack_ids:
            col_sel, col_btn = st.columns([2, 1])
            with col_sel:
                selected_id = st.selectbox("Select Alert ID to Acknowledge", options=unack_ids)
            with col_btn:
                st.write("")
                st.write("")
                if st.button("Acknowledge Alert"):
                    if db.acknowledge_alert(selected_id):
                        st.success(f"Alert #{selected_id} acknowledged.")
                        st.rerun()
    else:
        st.success("No alert events recorded matching current criteria.")

    st.markdown("---")
    st.subheader("Configured Threshold Limits")
    thresh_data = [
        {"Resource Metric": "CPU Utilization", "Warning Threshold": "≥ 80.0%", "Critical Limit": "≥ 90.0%", "Evaluation Type": "Instantaneous & Z-Score"},
        {"Resource Metric": "Physical RAM", "Warning Threshold": "≥ 85.0%", "Critical Limit": "≥ 95.0%", "Evaluation Type": "Memory Pressure Index"},
        {"Resource Metric": "Disk Storage", "Warning Threshold": "≥ 85.0%", "Critical Limit": "≥ 92.0%", "Evaluation Type": "Primary Partition Capacity"},
        {"Resource Metric": "Statistical Anomaly", "Warning Threshold": "Z ≥ 2.5σ", "Critical Limit": "Z ≥ 3.5σ", "Evaluation Type": "Rolling Baseline (40 Samples)"},
        {"Resource Metric": "Alert Cooldown", "Warning Threshold": "60 Seconds", "Critical Limit": "60 Seconds", "Evaluation Type": "Deduplication Window"},
    ]
    st.dataframe(pd.DataFrame(thresh_data), hide_index=True, use_container_width=True)
