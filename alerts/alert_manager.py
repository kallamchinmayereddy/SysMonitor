"""
SysMonitor Alert Management System
Evaluates resource thresholds, enforces cooldown deduplication,
tracks active vs historical alerts, and persists alert events.
"""
import time
from typing import Any, Dict, List, Optional
from analytics.anomaly_detector import AnomalyDetector
from config.settings import (
    ALERT_COOLDOWN_SECONDS,
    CPU_CRITICAL_THRESHOLD,
    CPU_WARNING_THRESHOLD,
    DISK_CRITICAL_THRESHOLD,
    DISK_WARNING_THRESHOLD,
    MEMORY_CRITICAL_THRESHOLD,
    MEMORY_WARNING_THRESHOLD,
)
from database.db_manager import DatabaseManager
from utils.logger import get_logger

logger = get_logger("AlertManager")


class AlertManager:
    """Manages threshold checking, deduplication cooldowns, and alert persistence."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        cpu_warn: float = CPU_WARNING_THRESHOLD,
        cpu_crit: float = CPU_CRITICAL_THRESHOLD,
        mem_warn: float = MEMORY_WARNING_THRESHOLD,
        mem_crit: float = MEMORY_CRITICAL_THRESHOLD,
        disk_warn: float = DISK_WARNING_THRESHOLD,
        disk_crit: float = DISK_CRITICAL_THRESHOLD,
        cooldown_seconds: float = ALERT_COOLDOWN_SECONDS,
    ):
        self.db_manager = db_manager or DatabaseManager.get_instance()
        self.cpu_warn = cpu_warn
        self.cpu_crit = cpu_crit
        self.mem_warn = mem_warn
        self.mem_crit = mem_crit
        self.disk_warn = disk_warn
        self.disk_crit = disk_crit
        self.cooldown_seconds = cooldown_seconds

        self.anomaly_detector = AnomalyDetector()
        self._last_alert_time: Dict[str, float] = {}
        logger.info("AlertManager initialized with cooldown %.0fs", cooldown_seconds)

    def _should_trigger(self, alert_key: str, now: float) -> bool:
        """Determines if enough cooldown time has elapsed since the last alert of this type."""
        last_time = self._last_alert_time.get(alert_key, 0.0)
        if (now - last_time) >= self.cooldown_seconds:
            self._last_alert_time[alert_key] = now
            return True
        return False

    def check_metrics(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluates unified system metrics against thresholds and anomaly baselines.
        Saves triggered alerts to database and returns a list of newly fired alerts.
        """
        now = metrics.get("timestamp", time.time())
        new_alerts: List[Dict[str, Any]] = []

        # 1. CPU Threshold Check
        cpu = metrics.get("cpu_percent")
        if cpu is not None:
            if cpu >= self.cpu_crit:
                key = "CPU_Critical"
                if self._should_trigger(key, now):
                    msg = f"Critical CPU saturation: {cpu:.1f}% exceeds critical limit of {self.cpu_crit:.1f}%"
                    row_id = self.db_manager.insert_alert_event("CPU", "Critical", msg, cpu, self.cpu_crit, now)
                    new_alerts.append({"id": row_id, "type": "CPU", "severity": "Critical", "message": msg, "time": now})
            elif cpu >= self.cpu_warn:
                key = "CPU_Warning"
                if self._should_trigger(key, now):
                    msg = f"Elevated CPU usage: {cpu:.1f}% exceeds warning threshold of {self.cpu_warn:.1f}%"
                    row_id = self.db_manager.insert_alert_event("CPU", "Warning", msg, cpu, self.cpu_warn, now)
                    new_alerts.append({"id": row_id, "type": "CPU", "severity": "Warning", "message": msg, "time": now})

        # 2. Memory Threshold Check
        mem = metrics.get("memory_percent")
        if mem is not None:
            if mem >= self.mem_crit:
                key = "Memory_Critical"
                if self._should_trigger(key, now):
                    msg = f"Critical RAM exhaustion: {mem:.1f}% exceeds critical limit of {self.mem_crit:.1f}%"
                    row_id = self.db_manager.insert_alert_event("Memory", "Critical", msg, mem, self.mem_crit, now)
                    new_alerts.append({"id": row_id, "type": "Memory", "severity": "Critical", "message": msg, "time": now})
            elif mem >= self.mem_warn:
                key = "Memory_Warning"
                if self._should_trigger(key, now):
                    msg = f"High RAM usage: {mem:.1f}% exceeds warning threshold of {self.mem_warn:.1f}%"
                    row_id = self.db_manager.insert_alert_event("Memory", "Warning", msg, mem, self.mem_warn, now)
                    new_alerts.append({"id": row_id, "type": "Memory", "severity": "Warning", "message": msg, "time": now})

        # 3. Disk Threshold Check
        disk = metrics.get("disk_percent")
        if disk is not None:
            if disk >= self.disk_crit:
                key = "Disk_Critical"
                if self._should_trigger(key, now):
                    msg = f"Critical storage capacity: {disk:.1f}% exceeds critical limit of {self.disk_crit:.1f}%"
                    row_id = self.db_manager.insert_alert_event("Disk", "Critical", msg, disk, self.disk_crit, now)
                    new_alerts.append({"id": row_id, "type": "Disk", "severity": "Critical", "message": msg, "time": now})
            elif disk >= self.disk_warn:
                key = "Disk_Warning"
                if self._should_trigger(key, now):
                    msg = f"Constrained storage capacity: {disk:.1f}% exceeds warning threshold of {self.disk_warn:.1f}%"
                    row_id = self.db_manager.insert_alert_event("Disk", "Warning", msg, disk, self.disk_warn, now)
                    new_alerts.append({"id": row_id, "type": "Disk", "severity": "Warning", "message": msg, "time": now})

        # 4. Statistical Anomaly Detection
        anomalies = self.anomaly_detector.evaluate_snapshot(metrics)
        for a in anomalies:
            key = f"Anomaly_{a['metric_name']}"
            if self._should_trigger(key, now):
                msg = f"Statistical Anomaly: {a['reason']}"
                row_id = self.db_manager.insert_alert_event(
                    "Anomaly", "Warning", msg, a["observed_value"], a["threshold"], now
                )
                new_alerts.append({"id": row_id, "type": "Anomaly", "severity": "Warning", "message": msg, "time": now})

        return new_alerts
