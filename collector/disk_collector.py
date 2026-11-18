"""
SysMonitor Disk Metrics Collector
Gathers partition storage capacity, usage percentages, and calculates
instantaneous disk read/write throughput (bytes/s) using counter deltas.
"""
import time
from typing import Any, Dict, List, Optional
import psutil
from utils.logger import get_logger

logger = get_logger("DiskCollector")


class DiskCollector:
    """Collects disk partition capacities and instantaneous I/O throughput."""

    def __init__(self):
        self._prev_read_bytes: Optional[int] = None
        self._prev_write_bytes: Optional[int] = None
        self._prev_read_count: Optional[int] = None
        self._prev_write_count: Optional[int] = None
        self._prev_time: Optional[float] = None

        # Prime initial I/O state
        self._prime_io_counters()
        logger.debug("DiskCollector initialized")

    def _prime_io_counters(self) -> None:
        """Records initial I/O baseline to enable rate calculation on subsequent calls."""
        try:
            io = psutil.disk_io_counters()
            if io:
                self._prev_read_bytes = io.read_bytes
                self._prev_write_bytes = io.write_bytes
                self._prev_read_count = io.read_count
                self._prev_write_count = io.write_count
                self._prev_time = time.perf_counter()
        except Exception as e:
            logger.debug("Initial disk I/O baseline failed: %s", e)

    def collect(self) -> Dict[str, Any]:
        """
        Retrieves disk partition usage and computes instantaneous read/write rates.
        """
        now = time.time()
        curr_perf = time.perf_counter()

        # 1. Partition Capacities
        partitions_data: List[Dict[str, Any]] = []
        total_storage = 0
        used_storage = 0
        free_storage = 0

        seen_devices = set()
        try:
            for part in psutil.disk_partitions(all=False):
                # Filter out container/pseudo bind mounts (e.g. Kubernetes/Docker mounts in Streamlit Cloud)
                mp = part.mountpoint.lower()
                if mp.startswith(("/etc/", "/dev/", "/proc/", "/sys/", "/run/")):
                    continue

                # Deduplicate physical devices so the same disk is not double-counted across mounts
                dev_key = part.device if part.device else part.mountpoint
                if dev_key in seen_devices:
                    continue

                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    seen_devices.add(dev_key)
                    partitions_data.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "opts": part.opts,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": round(usage.percent, 1),
                    })
                    total_storage += usage.total
                    used_storage += usage.used
                    free_storage += usage.free
                except (PermissionError, OSError) as e:
                    logger.debug("Skipping inaccessible mount %s: %s", part.mountpoint, e)
                    continue
        except Exception as e:
            logger.warning("Error reading disk partitions: %s", e)

        aggregate_percent = round((used_storage / total_storage * 100.0), 1) if total_storage > 0 else 0.0

        # 2. Disk I/O Rates (Bytes/sec and IOPS)
        read_rate = 0.0
        write_rate = 0.0
        read_iops = 0.0
        write_iops = 0.0
        read_bytes_total = 0
        write_bytes_total = 0

        try:
            io = psutil.disk_io_counters()
            if io:
                read_bytes_total = io.read_bytes
                write_bytes_total = io.write_bytes

                if self._prev_time is not None and self._prev_read_bytes is not None:
                    delta_t = curr_perf - self._prev_time
                    if delta_t > 0:
                        delta_read = io.read_bytes - self._prev_read_bytes
                        delta_write = io.write_bytes - self._prev_write_bytes
                        delta_rc = io.read_count - (self._prev_read_count or io.read_count)
                        delta_wc = io.write_count - (self._prev_write_count or io.write_count)

                        # Counter reset check (system reboot or counter rollover)
                        if delta_read >= 0 and delta_write >= 0:
                            read_rate = delta_read / delta_t
                            write_rate = delta_write / delta_t
                            read_iops = delta_rc / delta_t
                            write_iops = delta_wc / delta_t

                # Update state
                self._prev_read_bytes = io.read_bytes
                self._prev_write_bytes = io.write_bytes
                self._prev_read_count = io.read_count
                self._prev_write_count = io.write_count
                self._prev_time = curr_perf
        except Exception as e:
            logger.debug("Disk I/O counters unavailable: %s", e)

        return {
            "timestamp": now,
            "partitions": partitions_data,
            "total_storage": total_storage,
            "used_storage": used_storage,
            "free_storage": free_storage,
            "disk_percent": aggregate_percent,
            "disk_read_bytes": read_bytes_total,
            "disk_write_bytes": write_bytes_total,
            "read_bytes_per_sec": round(read_rate, 2),
            "write_bytes_per_sec": round(write_rate, 2),
            "read_iops": round(read_iops, 1),
            "write_iops": round(write_iops, 1),
        }
