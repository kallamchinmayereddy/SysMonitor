"""
SysMonitor Process Metrics Collector
Safely scans active system processes, extracting PID, CPU, memory, thread counts,
and provides top resource consumer identification and filtering utilities.
"""
from datetime import datetime
import time
from typing import Any, Dict, List, Optional
import psutil
from utils.formatters import format_timestamp
from utils.logger import get_logger

logger = get_logger("ProcessCollector")


class ProcessCollector:
    """Collects system process snapshots with defensive exception handling."""

    def __init__(self):
        logger.debug("ProcessCollector initialized")

    def collect(self) -> Dict[str, Any]:
        """
        Enumerates all accessible processes and aggregates summary metrics.
        """
        now = time.time()
        process_list: List[Dict[str, Any]] = []

        attrs = [
            "pid",
            "name",
            "status",
            "cpu_percent",
            "memory_percent",
            "memory_info",
            "num_threads",
            "create_time",
            "username",
        ]

        running_count = 0
        sleeping_count = 0

        for proc in psutil.process_iter(attrs=attrs):
            try:
                info = proc.info
                status = info.get("status") or "unknown"
                if status == psutil.STATUS_RUNNING:
                    running_count += 1
                elif status == psutil.STATUS_SLEEPING:
                    sleeping_count += 1

                mem_info = info.get("memory_info")
                mem_rss_bytes = mem_info.rss if mem_info else 0
                mem_mb = round(mem_rss_bytes / (1024.0 * 1024.0), 2)
                mem_percent = round(info.get("memory_percent") or 0.0, 2)
                cpu_p = round(info.get("cpu_percent") or 0.0, 1)

                create_time = info.get("create_time") or now
                create_time_str = format_timestamp(create_time)

                process_list.append({
                    "pid": info.get("pid"),
                    "name": info.get("name") or "Unknown",
                    "status": status,
                    "cpu_percent": cpu_p,
                    "memory_percent": mem_percent,
                    "memory_mb": mem_mb,
                    "threads": info.get("num_threads") or 1,
                    "create_time": create_time,
                    "create_time_formatted": create_time_str,
                    "username": info.get("username") or "System",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logger.debug("Unexpected error reading process info: %s", e)
                continue

        # Extract Top 5 Consumers
        top_cpu = sorted(process_list, key=lambda x: x["cpu_percent"], reverse=True)[:5]
        top_memory = sorted(process_list, key=lambda x: x["memory_mb"], reverse=True)[:5]

        return {
            "timestamp": now,
            "total_processes": len(process_list),
            "running_count": running_count,
            "sleeping_count": sleeping_count,
            "processes": process_list,
            "top_cpu": top_cpu,
            "top_memory": top_memory,
        }

    @staticmethod
    def filter_processes(
        processes: List[Dict[str, Any]],
        search_query: str = "",
        sort_by: str = "cpu_percent",
        ascending: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filters and sorts a list of processes for dashboard presentation.
        """
        filtered = processes
        if search_query:
            query = search_query.lower()
            filtered = [
                p for p in filtered
                if query in str(p.get("name", "")).lower()
                or query in str(p.get("pid", ""))
                or query in str(p.get("username", "")).lower()
            ]

        # Valid sort keys
        valid_keys = {"cpu_percent", "memory_mb", "memory_percent", "pid", "name", "threads"}
        key = sort_by if sort_by in valid_keys else "cpu_percent"

        try:
            sorted_procs = sorted(filtered, key=lambda x: x.get(key, 0) or 0, reverse=not ascending)
        except Exception:
            sorted_procs = filtered

        if limit and limit > 0:
            return sorted_procs[:limit]
        return sorted_procs
