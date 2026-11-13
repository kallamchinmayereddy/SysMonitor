"""
SysMonitor Dashboard - Historical Analytics Page
Queries persistent SQLite database records across customizable timeframes
(15m, 1h, 6h, 24h, 7d, custom), renders multi-resource historical graphs,
computes aggregate statistics, and provides CSV data export.
"""
from datetime import datetime, timedelta
import time
from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from analytics.statistics import summarize_metrics_dataframe
from database.db_manager import DatabaseManager
from dashboard.styles import get_plotly_layout, render_metric_card
from utils.formatters import format_bytes, format_rate


@st.cache_data(ttl=10, show_spinner=False)
def load_cached_history(time_option: str, custom_start: Optional[float] = None, custom_end: Optional[float] = None) -> pd.DataFrame:
    """Queries and caches historical telemetry DataFrame with 10-second TTL."""
    db = DatabaseManager.get_instance()
    now = time.time()
    start_time = None
    end_time = now

    if time_option == "Last 15 Minutes":
        start_time = now - (15 * 60)
    elif time_option == "Last 1 Hour":
        start_time = now - 3600
    elif time_option == "Last 6 Hours":
        start_time = now - (6 * 3600)
    elif time_option == "Last 24 Hours":
        start_time = now - (24 * 3600)
    elif time_option == "Last 7 Days":
        start_time = now - (7 * 86400)
    elif time_option == "Custom Date Range":
        start_time = custom_start
        end_time = custom_end or now

    return db.get_metrics_range(start_time=start_time, end_time=end_time, limit=10000)


def render_history_page():
    """Renders the historical performance analytics and report export interface."""
    db = DatabaseManager.get_instance()

    st.title("Historical Performance Analytics")
    st.caption("Long-term resource utilization patterns and trend analysis powered by SQLite.")

    # Educational Guide Expander
    with st.expander("💡 How to Read Historical Analytics & Performance Statistics", expanded=False):
        st.markdown(
            """
**Understanding Long-Term Performance Metrics & Telemetry Analysis:**

- **Persistent SQLite Telemetry**:
  - Telemetry snapshots are persistently written to an embedded SQLite database using **WAL (Write-Ahead Logging)** mode. This ensures thread-safe concurrent recording without blocking dashboard reads.
- **Analysis Timeframe**:
  - Choose a standard window (15m, 1h, 6h, 24h, 7d) or specify an exact custom calendar date range to query the database.
- **Statistical Performance Metrics**:
  - **Current**: The most recent measurement in the selected window.
  - **Mean / Avg**: The true arithmetic average of resource utilization.
  - **Peak / Max**: The maximum recorded burst or spike.
  - **Min**: The lowest baseline utilization observed.
  - **Standard Deviation (Std Dev)**: Quantifies system volatility. A low value (e.g. ±2%) indicates stable, predictable load; a high value indicates spiky, intermittent bursts.
  - **95th Percentile (P95)**: Industry standard in systems engineering. Discards the top 5% of temporary transient spikes to show the sustained resource capacity your system actually demands.
- **CSV Data Export**:
  - Clicking **Export to CSV** formats raw database bytes into human-friendly units (GB, MB, KB/s) with readable timestamps (`YYYY-MM-DD HH:MM:SS`) ready for Excel or academic reports.
            """
        )

    # 1. Timeframe Selection Controls
    col_range, col_export = st.columns([3, 1])

    with col_range:
        time_option = st.selectbox(
            "Select Analysis Timeframe",
            options=[
                "Last 15 Minutes",
                "Last 1 Hour",
                "Last 6 Hours",
                "Last 24 Hours",
                "Last 7 Days",
                "Custom Date Range",
            ],
            index=1,
            help="Filter historical database telemetry records across standard durations or a custom date range.",
        )

    custom_start = None
    custom_end = None
    if time_option == "Custom Date Range":
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=1))
        with c_d2:
            end_date = st.date_input("End Date", datetime.now())
        custom_start = datetime.combine(start_date, datetime.min.time()).timestamp()
        custom_end = datetime.combine(end_date, datetime.max.time()).timestamp()

    # Query persistent database using cached accessor
    df = load_cached_history(time_option, custom_start=custom_start, custom_end=custom_end)

    with col_export:
        st.write("")
        st.write("")
        if not df.empty:
            csv_data = db.format_metrics_for_export(df).to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv_data,
                file_name=f"sysmonitor_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Download full human-readable telemetry dataset for the selected period",
            )

    if df.empty:
        st.warning(f"No historical records found for '{time_option}'. Keep the monitoring engine active to accumulate telemetry.")
        return

    if len(df) <= 1:
        st.info(
            "💡 **Single Snapshot Mode:** You currently have **1 recorded telemetry record**. "
            "To view an evolving continuous line chart and dynamic averages, click **'🔄 Refresh Now'** (top right) "
            "or enable **'Auto-Refresh'** / **'Continuous Background'** in the sidebar."
        )
    else:
        st.info(f"Loaded **{len(df):,}** historical telemetry records from SQLite database.")

    # 2. Statistical Summary Table
    st.subheader("Statistical Performance Summary")
    stats_dict = summarize_metrics_dataframe(df)

    stat_rows = []
    metric_labels = {
        "cpu_percent": ("CPU Utilization", "%"),
        "memory_percent": ("RAM Utilization", "%"),
        "disk_percent": ("Disk Utilization", "%"),
        "download_speed": ("Download Speed", "B/s"),
        "upload_speed": ("Upload Speed", "B/s"),
        "read_bytes_per_sec": ("Disk Read Throughput", "B/s"),
        "write_bytes_per_sec": ("Disk Write Throughput", "B/s"),
    }

    for key, (label, unit) in metric_labels.items():
        if key in stats_dict:
            s = stats_dict[key]
            if unit == "%":
                stat_rows.append({
                    "Resource Metric": label,
                    "Current": f"{s['current']:.1f}%",
                    "Mean / Avg": f"{s['mean']:.1f}%",
                    "Peak / Max": f"{s['max']:.1f}%",
                    "Min": f"{s['min']:.1f}%",
                    "Std Dev": f"±{s['std']:.1f}%",
                    "95th Percentile": f"{s['p95']:.1f}%",
                })
            else:
                stat_rows.append({
                    "Resource Metric": label,
                    "Current": format_rate(s["current"]),
                    "Mean / Avg": format_rate(s["mean"]),
                    "Peak / Max": format_rate(s["max"]),
                    "Min": format_rate(s["min"]),
                    "Std Dev": format_rate(s["std"]),
                    "95th Percentile": format_rate(s["p95"]),
                })

    st.dataframe(pd.DataFrame(stat_rows), hide_index=True, use_container_width=True)

    # 3. Interactive Historical Graphs
    marker_size = 7 if len(df) <= 3 else 3
    tab_cpu, tab_mem, tab_disk, tab_net = st.tabs([
        "💻 CPU Trend",
        "🧠 Memory Trend",
        "💾 Disk Activity",
        "🌐 Network Bandwidth",
    ])

    with tab_cpu:
        fig_cpu = go.Figure()
        fig_cpu.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["cpu_percent"],
            name="CPU %",
            line=dict(color="#58a6ff", width=2),
            mode="lines+markers",
            marker=dict(size=marker_size),
            fill="tozeroy",
            fillcolor="rgba(88, 166, 255, 0.1)",
        ))
        fig_cpu.update_layout(
            get_plotly_layout(
                title="Historical CPU Utilization (%)",
                height=340,
                xaxis_title="Timestamp",
                yaxis_title="CPU (%)",
            )
        )
        fig_cpu.update_xaxes(tickformat="%H:%M:%S")
        fig_cpu.update_yaxes(range=[0, 100])
        st.plotly_chart(fig_cpu, use_container_width=True)

    with tab_mem:
        fig_mem = go.Figure()
        fig_mem.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["memory_percent"],
            name="RAM %",
            line=dict(color="#3fb950", width=2),
            mode="lines+markers",
            marker=dict(size=marker_size),
            fill="tozeroy",
            fillcolor="rgba(63, 185, 80, 0.1)",
        ))
        fig_mem.update_layout(
            get_plotly_layout(
                title="Historical Physical RAM Utilization (%)",
                height=340,
                xaxis_title="Timestamp",
                yaxis_title="RAM (%)",
            )
        )
        fig_mem.update_xaxes(tickformat="%H:%M:%S")
        fig_mem.update_yaxes(range=[0, 100])
        st.plotly_chart(fig_mem, use_container_width=True)

    with tab_disk:
        fig_disk = go.Figure()
        fig_disk.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["read_bytes_per_sec"] / 1024.0,
            name="Read (KB/s)",
            line=dict(color="#3fb950", width=1.8),
            mode="lines+markers",
            marker=dict(size=marker_size),
        ))
        fig_disk.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["write_bytes_per_sec"] / 1024.0,
            name="Write (KB/s)",
            line=dict(color="#f0883e", width=1.8),
            mode="lines+markers",
            marker=dict(size=marker_size),
        ))
        fig_disk.update_layout(
            get_plotly_layout(
                title="Historical Disk I/O Transfer Rates (KB/s)",
                height=340,
                xaxis_title="Timestamp",
                yaxis_title="Rate (KB/s)",
            )
        )
        fig_disk.update_xaxes(tickformat="%H:%M:%S")
        st.plotly_chart(fig_disk, use_container_width=True)

    with tab_net:
        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["download_speed"] / 1024.0,
            name="Download (KB/s)",
            line=dict(color="#2f81f7", width=1.8),
            mode="lines+markers",
            marker=dict(size=marker_size),
        ))
        fig_net.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["upload_speed"] / 1024.0,
            name="Upload (KB/s)",
            line=dict(color="#bc8cff", width=1.8),
            mode="lines+markers",
            marker=dict(size=marker_size),
        ))
        fig_net.update_layout(
            get_plotly_layout(
                title="Historical Network Throughput (KB/s)",
                height=340,
                xaxis_title="Timestamp",
                yaxis_title="Speed (KB/s)",
            )
        )
        fig_net.update_xaxes(tickformat="%H:%M:%S")
        st.plotly_chart(fig_net, use_container_width=True)
