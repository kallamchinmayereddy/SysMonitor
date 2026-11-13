"""
SysMonitor Dashboard - CPU Analysis Page
Detailed breakdown of CPU performance: per-core loads, historical trends,
frequency scaling, and kernel/user time accounting.
"""
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from analytics.statistics import calculate_series_stats
from collector.monitoring_engine import MonitoringEngine
from dashboard.styles import get_plotly_layout, render_metric_card
from utils.formatters import format_frequency, format_percent
from utils.system_info import get_static_system_info


def render_cpu_page():
    """Renders the detailed CPU analysis view."""
    engine = MonitoringEngine.get_instance()
    sys_info = get_static_system_info()

    metrics = engine.get_latest_metrics()
    if not metrics:
        metrics = engine.trigger_single_collection()

    history = engine.get_recent_history()

    st.title("CPU Utilization & Core Analytics")
    st.caption(f"Hardware: **{sys_info['processor']}** | Physical Cores: **{sys_info['cpu_physical_cores']}** | Logical Threads: **{sys_info['cpu_logical_cores']}**")

    # Educational Guide Expander
    with st.expander("💡 How to Read CPU Metrics & Operating System Scheduling", expanded=False):
        st.markdown(
            """
**Understanding CPU Performance & Operating System Concepts:**

- **CPU Utilization (%)**: Represents the percentage of time the CPU spends executing instructions rather than idling in the OS idle loop. Loads below **70%** indicate healthy headroom; sustained loads above **85%** indicate heavy computational demand.
- **Physical Cores vs. Logical Threads**: Physical cores are physical processing units on the silicon chip. Logical threads (via SMT / Hyper-Threading) allow each core to maintain multiple hardware execution contexts, improving multitasking efficiency.
- **Dynamic Clock Frequency (MHz / GHz)**: Processors scale clock speed on the fly. The CPU drops frequency when idle to conserve battery and reduce heat, and boosts dynamically (Turbo Boost) when compute-heavy tasks arrive.
- **Execution States (User vs. System/Kernel vs. Idle)**:
  - **User Time**: Time spent running your user applications (browsers, IDEs, code).
  - **System / Kernel Time**: Time the OS kernel spent servicing hardware interrupts, executing system calls (I/O, memory allocation), and scheduling thread context switches.
  - **Idle Time**: Time the CPU waited with no work to execute.
- **Statistical Indicators**:
  - **Mean / Avg**: Your typical baseline workload.
  - **Std Dev (±)**: Measures workload volatility. High standard deviation indicates bursty, spiky workloads.
  - **95th Percentile (P95)**: The utilization level that 95% of observations did not exceed, showing your true sustained load by ignoring brief anomalies.
            """
        )

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

    # 1. Summary Statistics from History
    if df_hist is not None and not df_hist.empty and "cpu_percent" in df_hist.columns:
        cpu_history_values = df_hist["cpu_percent"].tolist()
    else:
        cpu_history_values = [metrics.get("cpu_percent", 0.0)]
    stats = calculate_series_stats(cpu_history_values)

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            render_metric_card("Current CPU", f"{stats['current']:.1f}%", f"Target: <80%"),
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            render_metric_card("Average CPU", f"{stats['mean']:.1f}%", f"Std Dev: ±{stats['std']:.1f}%"),
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            render_metric_card("Peak / Max CPU", f"{stats['max']:.1f}%", f"95th %ile: {stats['p95']:.1f}%"),
            unsafe_allow_html=True,
        )
    with s4:
        freq_curr = metrics.get("freq_current")
        st.markdown(
            render_metric_card(
                "CPU Frequency",
                format_frequency(freq_curr),
                f"Min/Max: {format_frequency(metrics.get('freq_min'))} / {format_frequency(metrics.get('freq_max'))}",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 2. Historical CPU Trend Chart
    if df_hist is not None and not df_hist.empty:
        df_hist["time_str"] = df_hist["timestamp"].apply(lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S"))

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df_hist["time_str"],
            y=df_hist["cpu_percent"],
            name="Overall CPU %",
            line=dict(color="#58a6ff", width=2.5),
            mode="lines+markers",
            marker=dict(size=5),
            fill="tozeroy",
            fillcolor="rgba(88, 166, 255, 0.12)",
        ))
        fig_trend.update_layout(
            get_plotly_layout(
                title="Historical CPU Utilization (% over time)",
                height=320,
                xaxis_title="Time",
                yaxis_title="CPU Utilization (%)",
            )
        )
        fig_trend.update_yaxes(range=[0, 100])
        st.plotly_chart(fig_trend, use_container_width=True)

    # 3. Per-Core Utilization Breakdown & CPU Times
    c_cores, c_times = st.columns([3, 2])

    with c_cores:
        st.subheader("Per-Core Thread Utilization")
        per_core = metrics.get("per_core", [])
        if per_core:
            core_labels = [f"Core {i}" for i in range(len(per_core))]
            colors = ["#f85149" if val >= 90 else ("#d29922" if val >= 75 else "#238636") for val in per_core]

            fig_cores = go.Figure(go.Bar(
                x=per_core,
                y=core_labels,
                orientation="h",
                marker_color=colors,
                text=[f"{v:.1f}%" for v in per_core],
                textposition="auto",
            ))
            fig_cores.update_layout(
                get_plotly_layout(
                    title="Current Load Per Logical Core",
                    height=280,
                    xaxis_title="Load (%)",
                    yaxis_title="Core",
                    show_legend=False,
                )
            )
            fig_cores.update_xaxes(range=[0, 100])
            st.plotly_chart(fig_cores, use_container_width=True)

    with c_times:
        st.subheader("CPU Execution Times")
        cpu_times = metrics.get("cpu_times", {})
        if cpu_times:
            total_time = sum(cpu_times.values()) if sum(cpu_times.values()) > 0 else 1.0
            times_df = pd.DataFrame([
                {"State": k.capitalize(), "Seconds": f"{v:,.1f}s", "Share": f"{(v/total_time*100):.1f}%"}
                for k, v in cpu_times.items()
                if v > 0
            ])
            st.dataframe(times_df, hide_index=True, use_container_width=True)

            # Donut chart for times
            labels = [k.capitalize() for k in cpu_times.keys() if cpu_times[k] > 0]
            values = [cpu_times[k] for k in cpu_times.keys() if cpu_times[k] > 0]
            fig_pie = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                textinfo="label+percent",
                marker=dict(colors=["#58a6ff", "#f85149", "#3fb950", "#bc8cff"]),
            ))
            fig_pie.update_layout(
                paper_bgcolor="#161b22",
                plot_bgcolor="#0d1117",
                height=200,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                font=dict(color="#c9d1d9"),
            )
            st.plotly_chart(fig_pie, use_container_width=True)
