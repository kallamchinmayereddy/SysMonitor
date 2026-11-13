"""
SysMonitor System Health Score Calculator
Calculates an explainable 0-100 heuristic system health indicator based on weighted
resource penalties, diagnostic reasons, and troubleshooting recommendations.
"""
from typing import Any, Dict, List, Optional
from config.settings import HEALTH_WEIGHT_CPU, HEALTH_WEIGHT_DISK, HEALTH_WEIGHT_MEM


class HealthScoreCalculator:
    """
    Heuristic system health indicator.
    Note: This is a performance optimization and load indicator,
    not a low-level hardware diagnostic.
    """

    def __init__(
        self,
        weight_cpu: float = HEALTH_WEIGHT_CPU,
        weight_mem: float = HEALTH_WEIGHT_MEM,
        weight_disk: float = HEALTH_WEIGHT_DISK,
    ):
        self.w_cpu = weight_cpu
        self.w_mem = weight_mem
        self.w_disk = weight_disk

    def calculate(
        self,
        cpu_percent: Optional[float],
        memory_percent: Optional[float],
        disk_percent: Optional[float],
    ) -> Dict[str, Any]:
        """
        Calculates health score (0-100), category, penalties, and recommendations.
        """
        reasons: List[str] = []
        recommendations: List[str] = []

        # 1. CPU Penalty Calculation
        cpu_penalty = 0.0
        if cpu_percent is not None:
            if cpu_percent > 50.0:
                cpu_penalty = ((cpu_percent - 50.0) / 50.0) * 100.0
                cpu_penalty = min(100.0, max(0.0, cpu_penalty))
            if cpu_percent >= 85.0:
                reasons.append(f"Severe CPU saturation ({cpu_percent:.1f}%)")
                recommendations.append("Identify and inspect runaway processes in Process Explorer.")
            elif cpu_percent >= 70.0:
                reasons.append(f"Elevated CPU load ({cpu_percent:.1f}%)")
                recommendations.append("Consider closing compute-heavy background applications.")

        # 2. Memory Penalty Calculation
        mem_penalty = 0.0
        if memory_percent is not None:
            if memory_percent > 60.0:
                mem_penalty = ((memory_percent - 60.0) / 40.0) * 100.0
                mem_penalty = min(100.0, max(0.0, mem_penalty))
            if memory_percent >= 90.0:
                reasons.append(f"Critical memory pressure ({memory_percent:.1f}%)")
                recommendations.append("Free RAM immediately by terminating idle browser tabs or memory leaks.")
            elif memory_percent >= 75.0:
                reasons.append(f"High memory utilization ({memory_percent:.1f}%)")
                recommendations.append("Monitor paging file swap activity to prevent thrashing.")

        # 3. Disk Penalty Calculation
        disk_penalty = 0.0
        if disk_percent is not None:
            if disk_percent > 70.0:
                disk_penalty = ((disk_percent - 70.0) / 30.0) * 100.0
                disk_penalty = min(100.0, max(0.0, disk_penalty))
            if disk_percent >= 90.0:
                reasons.append(f"Disk capacity exhaustion ({disk_percent:.1f}%)")
                recommendations.append("Purge temporary files, recycle bin, and outdated cache files.")
            elif disk_percent >= 80.0:
                reasons.append(f"Disk space constrained ({disk_percent:.1f}%)")
                recommendations.append("Review disk partition storage allocations.")

        # Total Weighted Penalty
        total_penalty = (
            (self.w_cpu * cpu_penalty)
            + (self.w_mem * mem_penalty)
            + (self.w_disk * disk_penalty)
        )
        score = round(max(0.0, min(100.0, 100.0 - total_penalty)), 1)

        # Categorization
        if score >= 90.0:
            category = "Optimal"
            status_color = "#00CC96"  # Green
        elif score >= 75.0:
            category = "Good"
            status_color = "#636EFA"  # Blue
        elif score >= 50.0:
            category = "Degraded"
            status_color = "#FFA15A"  # Amber
        else:
            category = "Critical"
            status_color = "#EF553B"  # Red

        if not reasons:
            reasons.append("All resource subsystems operating within optimal load parameters.")
            recommendations.append("System is running efficiently. No administrative action required.")

        return {
            "score": score,
            "category": category,
            "status_color": status_color,
            "penalties": {
                "cpu": round(cpu_penalty, 1),
                "memory": round(mem_penalty, 1),
                "disk": round(disk_penalty, 1),
            },
            "weights": {
                "cpu": self.w_cpu,
                "memory": self.w_mem,
                "disk": self.w_disk,
            },
            "reasons": reasons,
            "recommendations": recommendations,
        }
