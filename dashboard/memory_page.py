"""
SysMonitor Dashboard - Memory Analysis Page
Visualizes physical RAM allocation, swap memory utilization,
memory pressure warnings, and historical allocation trends.
"""
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from analytics.statistics import calculate_series_stats
from collector.monitoring_engine import MonitoringEngine
from dashboard.styles import get_plotly_layout, render_metric_card
from utils.formatters import format_bytes, format_percent


def render_memory_page():
    """Renders the detailed memory and swap analysis view."""
    engine = MonitoringEngine.get_instance()
    metrics = engine.get_latest_metrics()
    if not metrics:
        metrics = engine.trigger_single_collection()

    history = engine.get_recent_history()

    st.title("Memory & Swap Analytics")
    st.caption("Detailed physical RAM and virtual paging file resource breakdown.")

    # Educational Guide Expander
    with st.expander("💡 How to Read Memory Allocation & Virtual Memory Paging", expanded=False):
        st.markdown(
            """
**Understanding Memory Hierarchy & Virtual Memory Concepts:**

- **Physical RAM (Random Access Memory)**: High-speed hardware memory where the OS keeps currently active code, kernel structures, and running processes.
- **Used vs. Available RAM**:
  - **Used Memory**: RAM actively allocated to applications, services, and the OS kernel.
  - **Available Memory**: Free RAM plus cached memory that can be immediately reclaimed by the OS kernel for new programs without causing page-outs.
- **Virtual Memory & Swap / Paging File**:
  - When physical RAM approaches capacity, the OS Virtual Memory Manager (VMM) migrates inactive memory pages out of RAM and writes them to a hidden file on your SSD/HDD (e.g., `pagefile.sys` on Windows).
  - High swap utilization is a warning sign: secondary storage is significantly slower than silicon RAM, which can trigger **disk thrashing** (where the OS spends more time swapping pages than running programs).
- **Memory Pressure Indicator**:
  - 🟢 **Normal (<75%)**: Abundant headroom, smooth multitasking.
  - 🟡 **Moderate (75%–85%)**: Elevated memory usage; OS begins background cache management.
  - 🟠 **High (85%–95%)**: High pressure; inactive pages are moved to swap.
  - 🔴 **Critical (>95%)**: Imminent risk of performance degradation, paging lag, or out-of-memory errors.
            """
        )

    # 1. Metric Cards
    mem_total = metrics.get("memory_total", 0)
    mem_used = metrics.get("memory_used", 0)
    mem_avail = metrics.get("memory_available", 0)
    mem_pct = metrics.get("memory_percent", 0.0)
    pressure = metrics.get("memory_pressure", "Normal")

    swap_total = metrics.get("swap_total", 0)
    swap_used = metrics.get("swap_used", 0)
    swap_pct = metrics.get("swap_percent", 0.0)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            render_metric_card("RAM Utilization", f"{mem_pct:.1f}%", f"Total: {format_bytes(mem_total)}"),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            render_metric_card("Used Memory", format_bytes(mem_used), f"Available: {format_bytes(mem_avail)}"),
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            render_metric_card("Swap / Paging", f"{swap_pct:.1f}%", f"Used: {format_bytes(swap_used)} / {format_bytes(swap_total)}"),
            unsafe_allow_html=True,
        )
    with m4:
        p_badge = "optimal" if pressure == "Normal" else ("warning" if pressure in ["Moderate", "High"] else "critical")
        st.markdown(
            render_metric_card("Memory Pressure", pressure, "Paging stability indicator", badge_text=pressure, badge_type=p_badge),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 2. Allocation Donut & Swap Progress
    col_donut, col_swap = st.columns([1, 1])

    with col_donut:
        st.subheader("Physical RAM Allocation")
        fig_donut = go.Figure(go.Pie(
            labels=["Used RAM", "Available RAM"],
            values=[mem_used, mem_avail],
            hole=0.55,
            marker=dict(colors=["#f85149" if mem_pct >= 85 else "#58a6ff", "#238636"]),
            textinfo="label+percent",
        ))
        fig_donut.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#0d1117",
            height=250,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=True,
            legend=dict(font=dict(color="#c9d1d9")),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_swap:
        st.subheader("Virtual Memory (Swap) Allocation")
        fig_swap = go.Figure(go.Indicator(
            mode="gauge+number",
            value=swap_pct,
            title={"text": "Swap File Utilization (%)", "font": {"color": "#c9d1d9", "size": 14}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                "bar": {"color": "#bc8cff"},
                "bgcolor": "#161b22",
                "steps": [
                    {"range": [0, 50], "color": "rgba(56, 139, 253, 0.15)"},
                    {"range": [50, 80], "color": "rgba(210, 153, 34, 0.25)"},
                    {"range": [80, 100], "color": "rgba(248, 81, 73, 0.25)"},
                ],
            },
        ))
        fig_swap.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#0d1117",
            height=250,
            margin=dict(l=20, r=20, t=20, b=20),
            font=dict(color="#c9d1d9"),
        )
        st.plotly_chart(fig_swap, use_container_width=True)

    # 3. Memory Usage History
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
        st.subheader("Memory Allocation History")
        df_hist["time_str"] = df_hist["timestamp"].apply(lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S"))

        fig_mem = go.Figure()
        fig_mem.add_trace(go.Scatter(
            x=df_hist["time_str"],
            y=df_hist["memory_percent"],
            name="RAM %",
            line=dict(color="#3fb950", width=2.5),
            mode="lines+markers",
            marker=dict(size=5),
            fill="tozeroy",
            fillcolor="rgba(63, 185, 80, 0.12)",
        ))
        swap_vals = (
            df_hist["swap_percent"]
            if "swap_percent" in df_hist.columns
            else [metrics.get("swap_percent", 0.0)] * len(df_hist)
        )
        fig_mem.add_trace(go.Scatter(
            x=df_hist["time_str"],
            y=swap_vals,
            name="Swap %",
            line=dict(color="#bc8cff", width=1.5, dash="dot"),
            mode="lines+markers",
            marker=dict(size=4),
        ))
        fig_mem.update_layout(
            get_plotly_layout(
                title="RAM and Swap Utilization Over Time (%)",
                height=300,
                xaxis_title="Time",
                yaxis_title="Percent (%)",
            )
        )
        fig_mem.update_yaxes(range=[0, 100])
        st.plotly_chart(fig_mem, use_container_width=True)
