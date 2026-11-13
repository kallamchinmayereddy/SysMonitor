"""
SysMonitor Dashboard - Process Explorer Page
Comprehensive operating system task manager interface providing real-time
process enumeration, sorting, dynamic searching, and top resource consumer tracking.
"""
import pandas as pd
import streamlit as st
from collector.monitoring_engine import MonitoringEngine
from collector.process_collector import ProcessCollector
from dashboard.styles import render_metric_card


def render_process_page():
    """Renders the interactive process explorer view."""
    engine = MonitoringEngine.get_instance()
    proc_data = engine.get_latest_processes()

    if not proc_data or not proc_data.get("processes"):
        # Trigger an immediate scan if empty
        with st.spinner("Enumerating active system processes..."):
            proc_data = engine.process_collector.collect()

    all_procs = proc_data.get("processes", [])
    total_procs = len(all_procs)
    running_count = proc_data.get("running_count", 0)
    sleeping_count = proc_data.get("sleeping_count", 0)

    st.title("Process Explorer & Task Manager")
    st.caption("Inspect and analyze all active tasks running on the operating system.")

    # Educational Guide Expander
    with st.expander("💡 How to Read the Process Explorer & OS Task Management", expanded=False):
        st.markdown(
            """
**Understanding Operating System Process & Thread Management:**

- **What is a Process?**:
  - An independent executing instance of a computer program, allocated its own virtual address space, memory pages, open file handles, and security context.
- **Process ID (PID)**:
  - A unique integer assigned by the OS kernel to track and schedule each process lifecycle.
- **Process Execution States**:
  - **Running**: The process is actively executing instructions on a CPU logical thread.
  - **Sleeping / Waiting**: The process is suspended in the kernel wait queue, awaiting an external event (e.g. keyboard input, network packet arrival, or disk I/O completion). On modern systems, >95% of processes are sleeping to avoid wasting CPU cycles.
- **Threads vs. Processes**:
  - A process can contain multiple concurrent **threads**. Threads within the same process share memory and heap space, enabling lightweight parallel execution without heavy context-switching overhead.
- **Filtering & Search**:
  - Use the search bar to locate specific applications (e.g. `chrome`, `python`, `code`) or sort by CPU % and Memory (MB) to identify resource hogs.
- **Operating System Stability Policy**:
  - For system security and stability, process termination is intentionally prohibited to protect critical OS kernel services (such as `services.exe`, `lsass.exe`, and `csrss.exe`) from accidental disruption.
            """
        )

    # 1. Summary Cards
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown(
            render_metric_card("Total Processes", str(total_procs), "Active in kernel process table"),
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            render_metric_card("Running Tasks", str(running_count), "Currently scheduled on CPU", badge_text="Running", badge_type="optimal"),
            unsafe_allow_html=True,
        )
    with p3:
        st.markdown(
            render_metric_card("Sleeping / Idle", str(sleeping_count), "Waiting on I/O or events"),
            unsafe_allow_html=True,
        )
    with p4:
        total_threads = sum(p.get("threads", 1) for p in all_procs)
        st.markdown(
            render_metric_card("Total Active Threads", f"{total_threads:,}", "Operating system thread pool"),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 2. Top Consumers Quick Columns
    c_cpu, c_mem = st.columns(2)

    with c_cpu:
        st.subheader("Top 5 by CPU Consumption")
        top_cpu = proc_data.get("top_cpu", [])
        if top_cpu:
            cpu_display = [
                {
                    "PID": p["pid"],
                    "Name": p["name"],
                    "CPU %": f"{p['cpu_percent']:.1f}%",
                    "Memory": f"{p['memory_mb']:.1f} MB",
                    "Threads": p["threads"],
                }
                for p in top_cpu
            ]
            st.dataframe(pd.DataFrame(cpu_display), hide_index=True, use_container_width=True)

    with c_mem:
        st.subheader("Top 5 by Memory Consumption")
        top_mem = proc_data.get("top_memory", [])
        if top_mem:
            mem_display = [
                {
                    "PID": p["pid"],
                    "Name": p["name"],
                    "Memory": f"{p['memory_mb']:.1f} MB",
                    "RAM %": f"{p['memory_percent']:.1f}%",
                    "User": p["username"],
                }
                for p in top_mem
            ]
            st.dataframe(pd.DataFrame(mem_display), hide_index=True, use_container_width=True)

    st.markdown("---")

    # 3. Interactive Search, Filter, and Sort Controls
    st.subheader("Active Process Table")

    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([3, 2, 2, 2])
    with ctrl1:
        search_query = st.text_input(
            "🔍 Search Process Name, PID, or User",
            placeholder="e.g. python, chrome, 1240...",
            help="Case-insensitive substring filter matching process name, process ID (PID), or operating system user.",
        )
    with ctrl2:
        sort_by = st.selectbox(
            "Sort By",
            options=["cpu_percent", "memory_mb", "memory_percent", "threads", "pid", "name"],
            format_func=lambda x: {
                "cpu_percent": "CPU Utilization (%)",
                "memory_mb": "Memory Usage (MB)",
                "memory_percent": "Memory Share (%)",
                "threads": "Thread Count",
                "pid": "Process ID (PID)",
                "name": "Process Name",
            }[x],
            help="Choose the primary metric to sort the process list by.",
        )
    with ctrl3:
        sort_order = st.selectbox(
            "Order",
            options=["Descending", "Ascending"],
            help="Descending shows highest values first (e.g. highest CPU/RAM consumers).",
        )
        ascending = sort_order == "Ascending"
    with ctrl4:
        limit_val = st.selectbox(
            "Show Rows",
            options=[25, 50, 100, 250, "All"],
            index=1,
            help="Number of process rows to display in the table.",
        )
        limit = None if limit_val == "All" else int(limit_val)

    # Filter and sort
    filtered_procs = ProcessCollector.filter_processes(
        all_procs,
        search_query=search_query,
        sort_by=sort_by,
        ascending=ascending,
        limit=limit,
    )

    if filtered_procs:
        table_procs = [
            {
                "PID": p["pid"],
                "Process Name": p["name"],
                "Status": p["status"],
                "CPU %": f"{p['cpu_percent']:.1f}%",
                "Memory (MB)": f"{p['memory_mb']:.1f} MB",
                "RAM %": f"{p['memory_percent']:.1f}%",
                "Threads": p["threads"],
                "Started": p["create_time_formatted"],
                "User": p["username"],
            }
            for p in filtered_procs
        ]
        st.dataframe(pd.DataFrame(table_procs), hide_index=True, use_container_width=True, height=450)
        st.caption(f"Showing **{len(table_procs)}** of **{total_procs}** active processes. *Process termination is intentionally disabled for operating system stability.*")
    else:
        st.warning(f"No processes matched the search term '{search_query}'.")
