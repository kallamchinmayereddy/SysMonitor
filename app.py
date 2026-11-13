"""
SysMonitor – Intelligent Real-Time System Resource Monitoring Platform
Main Streamlit Application Entrypoint (Configured for On-Demand Snapshots & Manual Refresh)
"""
from datetime import datetime
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from collector.monitoring_engine import MonitoringEngine
from config.settings import APP_NAME, APP_VERSION
from dashboard.alerts_page import render_alerts_page
from dashboard.cpu_page import render_cpu_page
from dashboard.disk_page import render_disk_page
from dashboard.history_page import render_history_page
from dashboard.memory_page import render_memory_page
from dashboard.network_page import render_network_page
from dashboard.overview import render_overview_page
from dashboard.process_page import render_process_page
from dashboard.styles import apply_custom_css
from utils.system_info import get_static_system_info


# Page Configuration
st.set_page_config(
    page_title=f"{APP_NAME} - OS Resource Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Dark Modern Theme Styling
apply_custom_css()

# Retrieve Singleton Engine & System Info
engine = MonitoringEngine.get_instance()
sys_info = get_static_system_info()


# --- Sidebar Navigation & Mode Controls ---
with st.sidebar:
    st.markdown(
        f'<div style="text-align: center; padding: 10px 0 15px 0;">'
        f'<h2 style="margin: 0; color: #58a6ff; font-weight: 800; letter-spacing: -0.5px;">⚡ {APP_NAME}</h2>'
        f'<div style="color: #8b949e; font-size: 0.8rem;">Operating Systems Resource Monitor v{APP_VERSION}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Host System Identity Card
    st.markdown(
        f'<div style="background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 10px; margin-bottom: 14px;">'
        f'<div style="font-size: 0.72rem; color: #8b949e; text-transform: uppercase;">Host Machine</div>'
        f'<div style="font-weight: 600; color: #f0f6fc; font-size: 0.88rem;">{sys_info["hostname"]}</div>'
        f'<div style="font-size: 0.72rem; color: #8b949e;">{sys_info["os_name"]} {sys_info["os_release"]} ({sys_info["architecture"]})</div>'
        f'<div style="font-size: 0.72rem; color: #58a6ff; margin-top: 4px;">Uptime: {sys_info["uptime_formatted"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Refresh Button (Prominent in Sidebar)
    if st.button("🔄 Refresh System Snapshot", use_container_width=True, type="primary", help="Immediately takes a fresh hardware telemetry snapshot of CPU, RAM, Disk, Network, and active processes."):
        # Explicit user request: triggers fresh instantaneous measurement
        engine.trigger_single_collection()
        st.rerun()

    # Monitoring Execution Mode Selector
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.markdown("**Monitoring Mode**")
    mode_selection = st.radio(
        "Mode",
        options=["⚡ On-Demand (Manual Snapshot)", "🔄 Continuous Background"],
        index=0,  # Default: On-Demand (Zero idle background load)
        help="Choose 'On-Demand' for 0% idle CPU overhead (takes snapshots only on page refresh). Choose 'Continuous' to record continuous 1-second telemetry to SQLite.",
        label_visibility="collapsed",
    )

    if mode_selection == "🔄 Continuous Background":
        if not engine.is_running():
            engine.start(sampling_interval=1.0)
        st.caption("🟢 Background service active (1s sampling).")
    else:
        if engine.is_running():
            engine.stop()
        st.caption("💤 On-Demand mode: 0% idle CPU overhead. Samples on refresh.")

    st.markdown("---")

    # Navigation Menu
    nav_selection = st.radio(
        "Navigation",
        options=[
            "⚡ Overview",
            "💻 CPU Analysis",
            "🧠 Memory Analysis",
            "💾 Disk Storage & I/O",
            "🌐 Network Traffic",
            "📋 Process Explorer",
            "📈 Historical Analytics",
            "🚨 Alerts & Health Score",
        ],
        index=0,
        help="Select a specialized telemetry view or analysis console.",
    )

    st.markdown("---")

    # Optional Auto-Refresh (Off by default as requested)
    auto_refresh = st.checkbox("Auto-Refresh (Optional)", value=False, help="Automatically refreshes the dashboard view at the specified interval so you don't have to click Refresh manually.")
    if auto_refresh:
        refresh_rate = st.slider("Refresh Interval (s)", min_value=2, max_value=10, value=3, step=1, help="Number of seconds between automatic screen refreshes (minimum 2s recommended for process enumeration).")
    else:
        st.caption("Auto-refresh is OFF. Dashboard only updates when you refresh.")

    # Sidebar Quick Guide Expander
    with st.expander("💡 Quick Guide & Feature Legend", expanded=False):
        st.markdown(
            """
**How SysMonitor Works:**

- **⚡ On-Demand Mode (Default)**:
  - Takes a fresh measurement only when you load or click **Refresh**.
  - **Zero CPU & Battery Overhead** while you are reading or idle.
- **🔄 Continuous Background Mode**:
  - Runs a background worker thread recording telemetry every 1 second into SQLite.
  - Useful when running long benchmarks or observing transient spikes.
- **Auto-Refresh**:
  - Automatically triggers the dashboard to refresh at your chosen interval (default 3 seconds).
- **100% Genuine Telemetry**:
  - All readings originate directly from operating system kernel APIs via `psutil`. No simulated or mock data.
            """
        )


# --- Instantaneous Snapshot Capture ---
# When in On-Demand mode, ensure an instantaneous snapshot is taken right on load/refresh
if not engine.is_running():
    # If no metrics yet or on manual rerun, sample current utilization
    if not engine.get_latest_metrics():
        engine.trigger_single_collection()

# Get latest snapshot timestamp
latest_m = engine.get_latest_metrics()
snapshot_time_str = datetime.fromtimestamp(latest_m.get("timestamp", time.time())).strftime("%Y-%m-%d %H:%M:%S")

# Top Header Status Bar
h1, h2 = st.columns([4, 1])
with h1:
    mode_badge = "⚡ On-Demand (Manual Snapshot)" if not engine.is_running() else "🔄 Continuous Monitoring Active"
    st.markdown(
        f"<div style='font-size: 0.85rem; color: #8b949e; padding: 4px 0 10px 0;'>"
        f"⏱ <b>Snapshot Recorded At:</b> <span style='color: #f0f6fc;'>{snapshot_time_str}</span> &nbsp;|&nbsp; "
        f"<b>Mode:</b> <span style='color: #58a6ff;'>{mode_badge}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
with h2:
    if st.button("🔄 Refresh Now", use_container_width=True, help="Take an instantaneous snapshot and update all dashboard charts."):
        engine.trigger_single_collection()
        st.rerun()


# --- Main Dashboard Router ---
if nav_selection == "⚡ Overview":
    render_overview_page()
elif nav_selection == "💻 CPU Analysis":
    render_cpu_page()
elif nav_selection == "🧠 Memory Analysis":
    render_memory_page()
elif nav_selection == "💾 Disk Storage & I/O":
    render_disk_page()
elif nav_selection == "🌐 Network Traffic":
    render_network_page()
elif nav_selection == "📋 Process Explorer":
    render_process_page()
elif nav_selection == "📈 Historical Analytics":
    render_history_page()
elif nav_selection == "🚨 Alerts & Health Score":
    render_alerts_page()


# Auto-refresh loop (Only if user explicitly enabled it)
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
