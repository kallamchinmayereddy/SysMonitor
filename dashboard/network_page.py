"""
SysMonitor Dashboard - Network Traffic & Interfaces Page
Visualizes active network adapters, IP allocations, packet statistics,
instantaneous upload/download speeds, and historical bandwidth trends.
"""
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from collector.monitoring_engine import MonitoringEngine
from dashboard.styles import get_plotly_layout, render_metric_card
from utils.formatters import format_bytes, format_rate


def render_network_page():
    """Renders the detailed network bandwidth and adapter status view."""
    engine = MonitoringEngine.get_instance()
    metrics = engine.get_latest_metrics()
    if not metrics:
        metrics = engine.trigger_single_collection()

    history = engine.get_recent_history()

    st.title("Network Traffic & Adapter Analytics")
    st.caption("Live bandwidth consumption, packet transmission integrity, and network adapter states.")

    # Educational Guide Expander
    with st.expander("💡 How to Read Network Bandwidth & Network Interface Concepts", expanded=False):
        st.markdown(
            """
**Understanding Network Telemetry & Operating System Networking:**

- **Instantaneous Bandwidth (Download vs. Upload)**:
  - **Download Speed (Inbound)**: Real-time throughput of data being received by your computer from the network/internet.
  - **Upload Speed (Outbound)**: Real-time throughput of data transmitted from your computer to external endpoints.
- **Cumulative Traffic Volume**:
  - Total bytes exchanged across all active network interfaces since system boot.
- **Packet Transmission & Integrity**:
  - **Packets Exchanged**: Operating systems encapsulate all network data into discrete packets (TCP segments or UDP datagrams).
  - **Errors & Drops**:
    - **Packet Drops**: Occur when the OS kernel network receive/transmit buffer fills up faster than the CPU can process socket requests.
    - **Packet Errors**: Occur due to physical layer signal degradation, Wi-Fi interference, or hardware checksum failures. A value of **0** indicates clean transmission integrity.
- **Network Interface Adapters & MTU**:
  - Shows physical NICs (Wi-Fi, Gigabit Ethernet) as well as virtual OS interfaces (WSL Virtual Switch, VPN tunnels, Loopback `127.0.0.1`).
  - **MTU (Maximum Transmission Unit)**: The maximum frame size (typically 1500 bytes) that can be transmitted without requiring IP packet fragmentation.
            """
        )

    # 1. Telemetry Cards
    down_speed = metrics.get("download_speed", 0.0)
    up_speed = metrics.get("upload_speed", 0.0)
    total_recv = metrics.get("network_received_bytes", 0)
    total_sent = metrics.get("network_sent_bytes", 0)
    packets_recv = metrics.get("packets_recv", 0)
    packets_sent = metrics.get("packets_sent", 0)
    drop_err = metrics.get("dropin", 0) + metrics.get("dropout", 0) + metrics.get("errin", 0) + metrics.get("errout", 0)

    n1, n2, n3, n4 = st.columns(4)
    with n1:
        st.markdown(
            render_metric_card("Download Speed", format_rate(down_speed), f"Total: {format_bytes(total_recv)}"),
            unsafe_allow_html=True,
        )
    with n2:
        st.markdown(
            render_metric_card("Upload Speed", format_rate(up_speed), f"Total: {format_bytes(total_sent)}"),
            unsafe_allow_html=True,
        )
    with n3:
        st.markdown(
            render_metric_card("Packets Exchanged", f"{(packets_recv + packets_sent):,}", f"Recv: {packets_recv:,} | Sent: {packets_sent:,}"),
            unsafe_allow_html=True,
        )
    with n4:
        drop_badge = "optimal" if drop_err == 0 else "warning"
        st.markdown(
            render_metric_card("Packet Errors / Drops", f"{drop_err:,}", "Transmission anomalies", badge_text="Clean" if drop_err == 0 else "Loss", badge_type=drop_badge),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 2. Historical Throughput Chart
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
        st.subheader("Bandwidth Throughput History (KB/s)")
        df_hist["time_str"] = df_hist["timestamp"].apply(lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S"))
        df_hist["down_kbs"] = df_hist["download_speed"] / 1024.0
        df_hist["up_kbs"] = df_hist["upload_speed"] / 1024.0

        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(
            x=df_hist["time_str"],
            y=df_hist["down_kbs"],
            name="Inbound / Download",
            line=dict(color="#2f81f7", width=2.5),
            mode="lines+markers",
            marker=dict(size=4),
            fill="tozeroy",
            fillcolor="rgba(47, 129, 247, 0.12)",
        ))
        fig_net.add_trace(go.Scatter(
            x=df_hist["time_str"],
            y=df_hist["up_kbs"],
            name="Outbound / Upload",
            line=dict(color="#bc8cff", width=2),
            mode="lines+markers",
            marker=dict(size=4),
            fill="tozeroy",
            fillcolor="rgba(188, 140, 255, 0.12)",
        ))
        fig_net.update_layout(
            get_plotly_layout(
                title="Instantaneous Transfer Rates (KB/s)",
                height=320,
                xaxis_title="Time",
                yaxis_title="Transfer Speed (KB/s)",
            )
        )
        st.plotly_chart(fig_net, use_container_width=True)

    # 3. Network Interface Adapters Table
    st.subheader("Network Interface Adapters")
    interfaces = metrics.get("interfaces", [])
    if interfaces:
        adapter_rows = []
        for iface in interfaces:
            addrs_str = ", ".join(iface["addresses"]) if iface["addresses"] else "No IP Assigned"
            adapter_rows.append({
                "Interface Name": iface["name"],
                "Link Status": "UP" if iface["isup"] else "DOWN",
                "Speed": f"{iface['speed_mbps']} Mbps" if iface["speed_mbps"] > 0 else "Dynamic",
                "MTU": iface["mtu"],
                "Assigned IP Addresses": addrs_str,
            })
        st.dataframe(pd.DataFrame(adapter_rows), hide_index=True, use_container_width=True)
    else:
        st.info("No network adapters detected.")
