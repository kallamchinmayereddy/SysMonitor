"""
SysMonitor Dashboard - Disk Storage & I/O Page
Visualizes mounted disk partitions, storage capacities, instantaneous
read/write transfer rates, IOPS, and historical I/O throughput.
"""
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from collector.monitoring_engine import MonitoringEngine
from dashboard.styles import get_plotly_layout, render_metric_card
from utils.formatters import format_bytes, format_percent, format_rate


def render_disk_page():
    """Renders the detailed disk partition and I/O throughput view."""
    engine = MonitoringEngine.get_instance()
    metrics = engine.get_latest_metrics()
    if not metrics:
        metrics = engine.trigger_single_collection()

    history = engine.get_recent_history()

    st.title("Disk Storage & I/O Analytics")
    st.caption("Distinguishes static filesystem capacity from real-time dynamic disk transfer activity.")

    # Educational Guide Expander
    with st.expander("💡 How to Read Disk Storage vs. Dynamic I/O Throughput", expanded=False):
        st.markdown(
            """
**Understanding Secondary Storage & Disk I/O Subsystems:**

- **Static Capacity vs. Dynamic I/O Throughput**:
  - **Static Storage Capacity**: The static size of your disk partitions (e.g., C: and D: drives), showing how much filesystem space is consumed vs. free.
  - **Dynamic I/O Throughput (KB/s or MB/s)**: The real-time rate at which data is being read from or written to the physical storage media right now. Spikes occur when loading apps, copying files, or running database queries.
- **IOPS (Input/Output Operations Per Second)**:
  - Measures the frequency of discrete read/write transactions handled by the disk controller.
  - High IOPS with low throughput indicates random access of many tiny files (e.g., compiling code or operating system logging). Low IOPS with high throughput indicates large sequential transfers (e.g., streaming a 4K video).
- **Filesystem Partitions**:
  - Displays partition mountpoints, filesystem types (NTFS, FAT32, APFS, ext4), and volume allocations managed by the OS storage subsystem.
            """
        )

    # 1. Metric Cards
    total_storage = metrics.get("total_storage", 0)
    used_storage = metrics.get("used_storage", 0)
    free_storage = metrics.get("free_storage", 0)
    disk_pct = metrics.get("disk_percent", 0.0)

    read_rate = metrics.get("read_bytes_per_sec", 0.0)
    write_rate = metrics.get("write_bytes_per_sec", 0.0)
    read_iops = metrics.get("read_iops", 0.0)
    write_iops = metrics.get("write_iops", 0.0)

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(
            render_metric_card("Aggregate Storage", f"{disk_pct:.1f}%", f"Total: {format_bytes(total_storage)}"),
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown(
            render_metric_card("Free Storage", format_bytes(free_storage), f"Used: {format_bytes(used_storage)}"),
            unsafe_allow_html=True,
        )
    with d3:
        st.markdown(
            render_metric_card("Disk Read Throughput", format_rate(read_rate), f"IOPS: {read_iops:,.0f} ops/s"),
            unsafe_allow_html=True,
        )
    with d4:
        st.markdown(
            render_metric_card("Disk Write Throughput", format_rate(write_rate), f"IOPS: {write_iops:,.0f} ops/s"),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 2. Partition Capacities Table and Progress
    st.subheader("Mounted Partitions & Volumes")
    partitions = metrics.get("partitions", [])
    if partitions:
        part_rows = []
        for p in partitions:
            part_rows.append({
                "Drive": p["mountpoint"],
                "Device": p["device"],
                "Filesystem": p["fstype"],
                "Total": format_bytes(p["total"]),
                "Used": format_bytes(p["used"]),
                "Free": format_bytes(p["free"]),
                "Utilization": f"{p['percent']:.1f}%",
            })
        st.dataframe(pd.DataFrame(part_rows), hide_index=True, use_container_width=True)

        # Partition comparison chart
        drive_names = [p["mountpoint"] for p in partitions]
        used_gbs = [p["used"] / (1024**3) for p in partitions]
        free_gbs = [p["free"] / (1024**3) for p in partitions]

        fig_parts = go.Figure()
        fig_parts.add_trace(go.Bar(
            name="Used (GB)",
            x=drive_names,
            y=used_gbs,
            marker_color="#f85149",
        ))
        fig_parts.add_trace(go.Bar(
            name="Free (GB)",
            x=drive_names,
            y=free_gbs,
            marker_color="#238636",
        ))
        fig_parts.update_layout(
            get_plotly_layout(
                title="Storage Allocation per Partition (GB)",
                height=260,
                xaxis_title="Drive",
                yaxis_title="Capacity (GB)",
            ),
            barmode="stack",
        )
        st.plotly_chart(fig_parts, use_container_width=True)

    # 3. Dynamic Disk I/O History (Throughput rates)
    from database.db_manager import DatabaseManager
    db = DatabaseManager.get_instance()

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
        st.subheader("Real-Time Disk I/O Throughput (KB/s)")
        df_hist["time_str"] = df_hist["timestamp"].apply(lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S"))
        df_hist["read_kbs"] = df_hist["read_bytes_per_sec"] / 1024.0
        df_hist["write_kbs"] = df_hist["write_bytes_per_sec"] / 1024.0

        fig_io = go.Figure()
        fig_io.add_trace(go.Scatter(
            x=df_hist["time_str"],
            y=df_hist["read_kbs"],
            name="Read Throughput",
            line=dict(color="#3fb950", width=2),
            mode="lines+markers",
            marker=dict(size=4),
            fill="tozeroy",
            fillcolor="rgba(63, 185, 80, 0.1)",
        ))
        fig_io.add_trace(go.Scatter(
            x=df_hist["time_str"],
            y=df_hist["write_kbs"],
            name="Write Throughput",
            line=dict(color="#f0883e", width=2),
            mode="lines+markers",
            marker=dict(size=4),
            fill="tozeroy",
            fillcolor="rgba(240, 136, 62, 0.1)",
        ))
        fig_io.update_layout(
            get_plotly_layout(
                title="Disk Transfer Rate (Read/Write KB/s)",
                height=300,
                xaxis_title="Time",
                yaxis_title="Transfer Speed (KB/s)",
            )
        )
        st.plotly_chart(fig_io, use_container_width=True)
