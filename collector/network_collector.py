"""
SysMonitor Network Metrics Collector
Gathers network interface statuses, cumulative traffic, packet statistics,
and computes instantaneous upload/download transfer rates (bytes/s).
"""
import time
from typing import Any, Dict, List, Optional
import psutil
from utils.logger import get_logger

logger = get_logger("NetworkCollector")


class NetworkCollector:
    """Collects network interface information and instantaneous throughput."""

    def __init__(self):
        self._prev_bytes_sent: Optional[int] = None
        self._prev_bytes_recv: Optional[int] = None
        self._prev_packets_sent: Optional[int] = None
        self._prev_packets_recv: Optional[int] = None
        self._prev_time: Optional[float] = None

        self._prime_network_counters()
        logger.debug("NetworkCollector initialized")

    def _prime_network_counters(self) -> None:
        """Records initial network baseline for rate differentials."""
        try:
            io = psutil.net_io_counters()
            if io:
                self._prev_bytes_sent = io.bytes_sent
                self._prev_bytes_recv = io.bytes_recv
                self._prev_packets_sent = io.packets_sent
                self._prev_packets_recv = io.packets_recv
                self._prev_time = time.perf_counter()
        except Exception as e:
            logger.debug("Initial network baseline failed: %s", e)

    def collect(self) -> Dict[str, Any]:
        """
        Retrieves aggregate network traffic, per-interface statuses,
        and computes instantaneous upload and download speeds.
        """
        now = time.time()
        curr_perf = time.perf_counter()

        bytes_sent = 0
        bytes_recv = 0
        packets_sent = 0
        packets_recv = 0
        errin = 0
        errout = 0
        dropin = 0
        dropout = 0

        upload_speed = 0.0
        download_speed = 0.0

        try:
            io = psutil.net_io_counters()
            if io:
                bytes_sent = io.bytes_sent
                bytes_recv = io.bytes_recv
                packets_sent = io.packets_sent
                packets_recv = io.packets_recv
                errin = io.errin
                errout = io.errout
                dropin = io.dropin
                dropout = io.dropout

                if self._prev_time is not None and self._prev_bytes_sent is not None:
                    delta_t = curr_perf - self._prev_time
                    if delta_t > 0:
                        delta_sent = bytes_sent - self._prev_bytes_sent
                        delta_recv = bytes_recv - self._prev_bytes_recv

                        # Check for counter rollover/reset
                        if delta_sent >= 0 and delta_recv >= 0:
                            upload_speed = delta_sent / delta_t
                            download_speed = delta_recv / delta_t

                # Update baseline
                self._prev_bytes_sent = bytes_sent
                self._prev_bytes_recv = bytes_recv
                self._prev_packets_sent = packets_sent
                self._prev_packets_recv = packets_recv
                self._prev_time = curr_perf
        except Exception as e:
            logger.warning("Error collecting network I/O counters: %s", e)

        # Per-interface statuses
        interfaces_list: List[Dict[str, Any]] = []
        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()

            for if_name, if_stat in stats.items():
                ip_addresses = []
                if if_name in addrs:
                    for addr in addrs[if_name]:
                        # Filter to IPv4 / IPv6 addresses
                        if addr.family.name in ("AF_INET", "AF_INET6"):
                            ip_addresses.append(addr.address)

                interfaces_list.append({
                    "name": if_name,
                    "isup": if_stat.isup,
                    "speed_mbps": if_stat.speed,
                    "mtu": if_stat.mtu,
                    "addresses": ip_addresses,
                })
        except Exception as e:
            logger.debug("Error inspecting network interfaces: %s", e)

        return {
            "timestamp": now,
            "bytes_sent": bytes_sent,
            "bytes_recv": bytes_recv,
            "packets_sent": packets_sent,
            "packets_recv": packets_recv,
            "upload_speed": round(upload_speed, 2),
            "download_speed": round(download_speed, 2),
            "errin": errin,
            "errout": errout,
            "dropin": dropin,
            "dropout": dropout,
            "interfaces": interfaces_list,
        }
