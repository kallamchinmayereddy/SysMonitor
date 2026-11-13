"""
SysMonitor Static System Information Utility
Retrieves host OS, CPU hardware specification, RAM capacity, and uptime.
"""
from datetime import datetime
import os
import platform
import sys
import time
from typing import Any, Dict
import psutil
from utils.formatters import format_bytes, format_duration, format_timestamp
from utils.logger import get_logger

logger = get_logger("SystemInfo")


import functools

@functools.lru_cache(maxsize=1)
def get_processor_name() -> str:
    """Retrieves human-readable CPU brand/model name cross-platform (cached)."""
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return str(name).strip()
        except Exception as e:
            logger.debug("winreg CPU query failed: %s", e)

    # Fallback to platform.processor() or machine
    proc = platform.processor()
    if proc:
        return proc
    return platform.machine() or "Generic Processor"


@functools.lru_cache(maxsize=1)
def _get_static_hardware_base() -> Dict[str, Any]:
    """Caches immutable hardware and operating system parameters in memory."""
    boot_time_ts = psutil.boot_time()
    mem = psutil.virtual_memory()
    from collector.memory_collector import get_safe_swap_memory
    swap = get_safe_swap_memory()

    logical_cores = psutil.cpu_count(logical=True) or 1
    physical_cores = psutil.cpu_count(logical=False) or logical_cores

    return {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "processor": get_processor_name(),
        "cpu_logical_cores": logical_cores,
        "cpu_physical_cores": physical_cores,
        "total_ram_bytes": mem.total,
        "total_ram_formatted": format_bytes(mem.total),
        "total_swap_bytes": swap["total"],
        "total_swap_formatted": format_bytes(swap["total"]),
        "boot_time": boot_time_ts,
        "boot_time_formatted": format_timestamp(boot_time_ts),
        "python_version": platform.python_version(),
    }


def get_static_system_info() -> Dict[str, Any]:
    """
    Gathers static hardware and operating system parameters.
    Uses in-memory LRU caching for static properties and calculates dynamic uptime.
    """
    base = _get_static_hardware_base().copy()
    uptime_sec = time.time() - base["boot_time"]
    base["uptime_seconds"] = uptime_sec
    base["uptime_formatted"] = format_duration(uptime_sec)
    return base


def get_uptime_seconds() -> float:
    """Returns current system uptime in seconds."""
    return time.time() - psutil.boot_time()
