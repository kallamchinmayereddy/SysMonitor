"""
SysMonitor Dashboard - Overview Page
Displays high-level system telemetry cards, real-time resource trends,
top active processes, and recent alert events.
"""
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from analytics.health_score import HealthScoreCalculator
from collector.monitoring_engine import MonitoringEngine
from config.settings import RECENT_BUFFER_MAXLEN
from database.db_manager import DatabaseManager
from dashboard.styles import get_plotly_layout, render_metric_card
from utils.formatters import format_bytes, format_duration, format_percent, format_rate
from utils.system_info import get_static_system_info


def render_overview_page():
    """Renders the comprehensive overview monitoring dashboard."""
    engine = MonitoringEngine.get_instance()
    db = DatabaseManager.get_instance()
    sys_info = get_static_system_info()
    health_calc = HealthScoreCalculator()

    # Retrieve live snapshot
    metrics = engine.get_latest_metrics()
    if not metrics:
        metrics = engine.trigger_single_collection()

    history = engine.get_recent_history()
    proc_data = engine.get_latest_processes()

    # Calculate Health Score
    health = health_calc.calculate(
        cpu_percent=metrics.get("cpu_percent"),
        memory_percent=metrics.get("memory_percent"),
        disk_percent=metrics.get("disk_percent"),
    )

    st.title("⚡ System Overview Dashboard")
    st.caption(f"Host: **{sys_info['hostname']}** | Operating System: **{sys_info['os_name']} {sys_info['os_release']} ({sys_info['architecture']})** | Uptime: **{sys_info['uptime_formatted']}**")

    # Beginner-Friendly User Guide Expander
    with st.expander("💡 New here? Learn how to read this Overview dashboard", expanded=False):
        st.markdown(
            """
            Welcome to **SysMonitor**! This dashboard gives you a high-level command center for your computer's health:
            - **CPU Utilization**: Shows the current load on your processor. Values below **70%** are healthy. If it stays above **85%**, your computer is under heavy compute load.
            - **RAM (Memory)**: Shows how much of your physical RAM is in use. High RAM usage (>85%) can cause your system to slow down and use disk swap space.
            - **Storage**: Shows how much space remains on your primary disk. Low free space (<10%) can prevent temporary file creation and OS updates.
            - **System Health (0-100)**: An intelligent score calculated from all your resources. **90-100** is Optimal, **75-89** is Good, **50-74** is Degraded, and below **50** is Critical.
            - **Live Trend Graphs**: Shows how resource usage changes between refreshes.
            - **Top Processes**: Quickly tells you which running programs are consuming the most CPU and Memory right now.
            """
        )

    # 1. Top Telemetry Metric Cards
    c1, c2, c3, c4 = st.columns(4)

    # CPU Card
    cpu_val = metrics.get("cpu_percent", 0.0)
    cpu_badge = "critical" if cpu_val >= 90 else ("warning" if cpu_val >= 80 else "optimal")
    with c1:
        st.markdown(
            render_metric_card(
                title="CPU Utilization",
                value=f"{cpu_val:.1f}%",
                subtext=f"{sys_info['cpu_physical_cores']} Cores / {sys_info['cpu_logical_cores']} Threads",
                badge_text=f"{metrics.get('freq_current', 'N/A')} MHz" if metrics.get("freq_current") else "",
                badge_type=cpu_badge,
            ),
            unsafe_allow_html=True,
        )

    # Memory Card
    mem_val = metrics.get("memory_percent", 0.0)
    mem_used_str = format_bytes(metrics.get("memory_used", 0))
    mem_tot_str = format_bytes(metrics.get("memory_total", 0))
    mem_badge = "critical" if mem_val >= 90 else ("warning" if mem_val >= 85 else "optimal")
    with c2:
        st.markdown(
            render_metric_card(
                title="RAM Utilization",
                value=f"{mem_val:.1f}%",
                subtext=f"Used: {mem_used_str} / {mem_tot_str}",
                badge_text=metrics.get("memory_pressure", "Normal"),
                badge_type=mem_badge,
            ),
            unsafe_allow_html=True,
        )

    # Disk Card
    disk_val = metrics.get("disk_percent", 0.0)
    disk_free_str = format_bytes(metrics.get("free_storage", 0))
    disk_badge = "critical" if disk_val >= 90 else ("warning" if disk_val >= 80 else "optimal")
    with c3:
        st.markdown(
            render_metric_card(
                title="Storage Utilization",
                value=f"{disk_val:.1f}%",
                subtext=f"Free: {disk_free_str} available",
                badge_text=f"R:{format_rate(metrics.get('read_bytes_per_sec', 0))}",
                badge_type=disk_badge,
            ),
            unsafe_allow_html=True,
        )

    # Health & Network Card
    net_down = format_rate(metrics.get("download_speed", 0))
    net_up = format_rate(metrics.get("upload_speed", 0))
    with c4:
        st.markdown(
            render_metric_card(
                title="System Health",
                value=f"{health['score']:.0f}/100",
                subtext=f"Net: ↓ {net_down} | ↑ {net_up}",
                badge_text=health["category"],
                badge_type=health["category"].lower() if health["category"] in ["Optimal", "Warning", "Critical"] else "info",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 2. Live Trend Charts (Dual View)
    g1, g2 = st.columns(2)

    df_hist = None
    if len(history) > 1:
        df_hist = pd.DataFrame(history)
    else:
        recent_db = db.get_recent_metrics_df(limit=30)
        if not recent_db.empty:
            df_hist = recent_db
        elif history:
            df_hist = pd.DataFrame(history)

    if df_hist is not None and not df_hist.empty:
        df_hist["time_str"] = df_hist["timestamp"].apply(lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S"))

        with g1:
            # CPU & RAM Trend
            fig_res = go.Figure()
            fig_res.add_trace(go.Scatter(
                x=df_hist["time_str"],
                y=df_hist["cpu_percent"],
                name="CPU %",
                line=dict(color="#58a6ff", width=2),
                mode="lines+markers",
                marker=dict(size=4),
            ))
            fig_res.add_trace(go.Scatter(
                x=df_hist["time_str"],
                y=df_hist["memory_percent"],
                name="RAM %",
                line=dict(color="#3fb950", width=2),
                mode="lines+markers",
                marker=dict(size=4),
            ))
            fig_res.update_layout(
                get_plotly_layout(
                    title="Real-Time CPU & Memory Utilization (%)",
                    height=280,
                    xaxis_title="Time",
                    yaxis_title="Percent (%)",
                )
            )
            fig_res.update_yaxes(range=[0, 100])
            st.plotly_chart(fig_res, use_container_width=True)

        with g2:
            # Network Throughput Trend
            fig_net = go.Figure()
            # Convert to KB/s for chart readability
            df_hist["down_kbs"] = df_hist["download_speed"] / 1024.0
            df_hist["up_kbs"] = df_hist["upload_speed"] / 1024.0

            fig_net.add_trace(go.Scatter(
                x=df_hist["time_str"],
                y=df_hist["down_kbs"],
                name="Download (KB/s)",
                line=dict(color="#2f81f7", width=2),
                mode="lines+markers",
                marker=dict(size=4),
                fill="tozeroy",
                fillcolor="rgba(47, 129, 247, 0.1)",
            ))
            fig_net.add_trace(go.Scatter(
                x=df_hist["time_str"],
                y=df_hist["up_kbs"],
                name="Upload (KB/s)",
                line=dict(color="#bc8cff", width=2),
                mode="lines+markers",
                marker=dict(size=4),
            ))
            fig_net.update_layout(
                get_plotly_layout(
                    title="Network Throughput (KB/s)",
                    height=280,
                    xaxis_title="Time",
                    yaxis_title="Speed (KB/s)",
                )
            )
            st.plotly_chart(fig_net, use_container_width=True)

    # 3. Bottom Row: Top Processes & Active Alerts
    col_proc, col_alert = st.columns([3, 2])

    with col_proc:
        st.subheader("Top Resource-Consuming Processes")
        top_procs = proc_data.get("top_cpu", [])
        if top_procs:
            proc_display = [
                {
                    "PID": p["pid"],
                    "Name": p["name"],
                    "CPU %": f"{p['cpu_percent']:.1f}%",
                    "Memory (MB)": f"{p['memory_mb']:.1f} MB",
                    "Threads": p["threads"],
                    "User": p["username"],
                }
                for p in top_procs
            ]
            st.dataframe(pd.DataFrame(proc_display), hide_index=True, use_container_width=True)
        else:
            st.info("Scanning process table...")

    with col_alert:
        st.subheader("Recent System Alerts")
        alerts_df = db.get_alerts(limit=5)
        if not alerts_df.empty:
            for _, row in alerts_df.iterrows():
                sev_color = "red" if row["severity"] == "Critical" else "orange"
                ack_status = "Acknowledged" if row["acknowledged"] else "Active"
                st.markdown(
                    f"**:{sev_color}[[{row['severity']}]]** `{row['resource_type']}` – {row['message']}<br>"
                    f"<small style='color: #8b949e;'>{row.get('datetime', row['timestamp'])} | Status: {ack_status}</small>",
                    unsafe_allow_html=True,
                )
                st.markdown("<hr style='margin: 6px 0;'>", unsafe_allow_html=True)
        else:
            st.success("No active threshold violations. All resources normal.")
