"""
SysMonitor CPU Metrics Collector
Gathers overall utilization, per-core utilization, frequency, and CPU times.
"""
import time
from typing import Any, Dict, List, Optional
import psutil
from utils.logger import get_logger

logger = get_logger("CPUCollector")


class CPUCollector:
    """Collects real-time CPU performance statistics."""

    def __init__(self, sample_interval: float = 0.1):
        self.logical_cores: int = psutil.cpu_count(logical=True) or 1
        self.physical_cores: int = psutil.cpu_count(logical=False) or self.logical_cores
        self.sample_interval: float = sample_interval
        logger.debug("CPUCollector initialized (%d logical / %d physical cores)", self.logical_cores, self.physical_cores)

    def collect(self, interval: Optional[float] = None) -> Dict[str, Any]:
        """
        Retrieves instantaneous CPU utilization and breakdown.
        Uses a short 0.1s sampling window to guarantee genuine, accurate,
        non-zero readings on on-demand snapshots and initial page renders.
        """
        now = time.time()
        sample_win = interval if interval is not None else self.sample_interval
        try:
            # Measure per-core utilization across the 0.1s sampling window
            per_core: List[float] = psutil.cpu_percent(interval=sample_win, percpu=True)
            if per_core and len(per_core) > 0:
                overall_percent = round(sum(per_core) / len(per_core), 1)
            else:
                overall_percent = 0.0

            times = psutil.cpu_times()
            freq = psutil.cpu_freq()

            # CPU Frequency handling (may be None in some virtualized environments)
            freq_current = freq.current if freq else None
            freq_min = freq.min if freq else None
            freq_max = freq.max if freq else None

            # CPU times: user, system, idle (and Windows specific interrupt/dpc if available)
            times_dict = {
                "user": getattr(times, "user", 0.0),
                "system": getattr(times, "system", 0.0),
                "idle": getattr(times, "idle", 0.0),
                "interrupt": getattr(times, "interrupt", 0.0),
                "dpc": getattr(times, "dpc", 0.0),
            }

            return {
                "timestamp": now,
                "cpu_percent": overall_percent,
                "per_core": [round(c, 1) for c in per_core],
                "logical_cores": self.logical_cores,
                "physical_cores": self.physical_cores,
                "freq_current": round(freq_current, 1) if freq_current else None,
                "freq_min": round(freq_min, 1) if freq_min else None,
                "freq_max": round(freq_max, 1) if freq_max else None,
                "cpu_times": times_dict,
            }
        except Exception as e:
            logger.error("Error collecting CPU metrics: %s", e)
            return {
                "timestamp": now,
                "cpu_percent": 0.0,
                "per_core": [0.0] * self.logical_cores,
                "logical_cores": self.logical_cores,
                "physical_cores": self.physical_cores,
                "freq_current": None,
                "freq_min": None,
                "freq_max": None,
                "cpu_times": {"user": 0.0, "system": 0.0, "idle": 0.0},
            }
