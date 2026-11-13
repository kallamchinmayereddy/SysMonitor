"""
SysMonitor Memory Metrics Collector
Gathers physical RAM utilization, available/used memory, swap usage, and memory pressure.
"""
import platform
import time
from typing import Any, Dict
import psutil
from config.settings import MEMORY_CRITICAL_THRESHOLD, MEMORY_WARNING_THRESHOLD
from utils.logger import get_logger

logger = get_logger("MemoryCollector")


def get_safe_swap_memory() -> Dict[str, Any]:
    """Retrieves swap/pagefile memory safely with Windows PDH fallback."""
    try:
        swap = psutil.swap_memory()
        return {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": round(swap.percent, 1),
        }
    except Exception as e:
        logger.debug("psutil.swap_memory() failed (%s), using GlobalMemoryStatusEx fallback", e)
        if platform.system() == "Windows":
            try:
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    pf_total = max(0, stat.ullTotalPageFile - stat.ullTotalPhys)
                    pf_free = max(0, stat.ullAvailPageFile - stat.ullAvailPhys)
                    pf_used = max(0, pf_total - pf_free)
                    pf_pct = round((pf_used / pf_total * 100), 1) if pf_total > 0 else 0.0
                    return {
                        "total": pf_total,
                        "used": pf_used,
                        "free": pf_free,
                        "percent": pf_pct,
                    }
            except Exception as we:
                logger.debug("GlobalMemoryStatusEx fallback failed: %s", we)
        return {"total": 0, "used": 0, "free": 0, "percent": 0.0}


class MemoryCollector:
    """Collects real-time memory and swap metrics."""

    def __init__(self):
        logger.debug("MemoryCollector initialized")

    def _determine_pressure(self, percent: float, swap_percent: float) -> str:
        """Determines memory pressure classification based on RAM and Swap utilization."""
        if percent >= MEMORY_CRITICAL_THRESHOLD:
            return "Critical"
        if percent >= MEMORY_WARNING_THRESHOLD:
            return "High"
        if percent >= 75.0 or (swap_percent > 30.0):
            return "Moderate"
        return "Normal"

    def collect(self) -> Dict[str, Any]:
        """Retrieves instantaneous memory allocation and swap metrics."""
        now = time.time()
        try:
            mem = psutil.virtual_memory()
            swap = get_safe_swap_memory()

            pressure = self._determine_pressure(mem.percent, swap["percent"])

            return {
                "timestamp": now,
                "memory_total": mem.total,
                "memory_used": mem.used,
                "memory_available": mem.available,
                "memory_free": getattr(mem, "free", mem.available),
                "memory_percent": round(mem.percent, 1),
                "swap_total": swap["total"],
                "swap_used": swap["used"],
                "swap_free": swap["free"],
                "swap_percent": swap["percent"],
                "memory_pressure": pressure,
            }
        except Exception as e:
            logger.error("Error collecting memory metrics: %s", e)
            return {
                "timestamp": now,
                "memory_total": 0,
                "memory_used": 0,
                "memory_available": 0,
                "memory_free": 0,
                "memory_percent": 0.0,
                "swap_total": 0,
                "swap_used": 0,
                "swap_free": 0,
                "swap_percent": 0.0,
                "memory_pressure": "Unknown",
            }
