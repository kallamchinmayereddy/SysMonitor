"""
SysMonitor Multithreaded Monitoring Engine
Coordinates concurrent metric collection, maintains thread-safe bounded buffers,
and provides lifecycle controls (start/stop) with listener notifications.
"""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from collector.cpu_collector import CPUCollector
from collector.disk_collector import DiskCollector
from collector.memory_collector import MemoryCollector
from collector.network_collector import NetworkCollector
from collector.process_collector import ProcessCollector
from config.settings import (
    DEFAULT_SAMPLING_INTERVAL,
    PROCESS_SAMPLING_INTERVAL,
    RECENT_BUFFER_MAXLEN,
)
from utils.logger import get_logger

logger = get_logger("MonitoringEngine")


class MonitoringEngine:
    """
    Central thread-safe coordinator for background system resource monitoring.
    Implements a singleton pattern to prevent duplicate collection threads across
    Streamlit re-runs.
    """

    _instance: Optional["MonitoringEngine"] = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "MonitoringEngine":
        """Returns the process-wide singleton instance of the MonitoringEngine."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        # Prevent direct initialization if already created
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="SysMonitorCollector")

        # Sampling configuration
        self.sampling_interval: float = DEFAULT_SAMPLING_INTERVAL
        self.process_sampling_interval: float = PROCESS_SAMPLING_INTERVAL

        # Individual Collectors
        self.cpu_collector = CPUCollector()
        self.memory_collector = MemoryCollector()
        self.disk_collector = DiskCollector()
        self.network_collector = NetworkCollector()
        self.process_collector = ProcessCollector()

        # Database and Alert integrations
        from database.db_manager import DatabaseManager
        from alerts.alert_manager import AlertManager
        self.db_manager = DatabaseManager.get_instance()
        self.alert_manager = AlertManager(db_manager=self.db_manager)

        # Shared In-Memory Data Stores (Guarded by _lock)
        self._recent_metrics: deque = deque(maxlen=RECENT_BUFFER_MAXLEN)
        self._latest_metrics: Dict[str, Any] = {}
        self._latest_processes: Dict[str, Any] = {}
        self._last_process_collection_time: float = 0.0

        # Registered Listeners (e.g. Database writer, Alert manager, Anomaly detector)
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

        logger.info("MonitoringEngine initialized (Sampling: %.1fs, Process Interval: %.1fs, Buffer: %d)",
                    self.sampling_interval, self.process_sampling_interval, RECENT_BUFFER_MAXLEN)

    def is_running(self) -> bool:
        """Checks if the background monitoring thread is active."""
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def start(self, sampling_interval: Optional[float] = None) -> bool:
        """
        Starts the background monitoring loop in a dedicated thread.
        Idempotent: if already running, does not start duplicate threads.
        """
        with self._lock:
            if self.is_running():
                logger.debug("MonitoringEngine is already running. Start ignored.")
                return False

            if sampling_interval is not None and sampling_interval > 0:
                self.sampling_interval = sampling_interval

            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._run_loop,
                name="SysMonitorEngineWorker",
                daemon=True,
            )
            self._worker_thread.start()
            logger.info("MonitoringEngine background thread started (interval: %.1fs)", self.sampling_interval)
            return True

    def stop(self, timeout: float = 3.0) -> bool:
        """
        Gracefully signals and terminates the background monitoring thread.
        """
        if not self.is_running():
            return False

        logger.info("Stopping MonitoringEngine background thread...")
        self._stop_event.set()

        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning("Monitoring thread did not terminate within %.1f seconds", timeout)
            else:
                logger.info("MonitoringEngine background thread stopped successfully.")

        self._worker_thread = None
        return True

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback to receive every newly collected unified metrics snapshot."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unregisters a metrics listener."""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def _collect_unified_metrics(self) -> Dict[str, Any]:
        """
        Executes CPU, Memory, Disk, and Network collectors concurrently using ThreadPoolExecutor.
        """
        future_cpu = self._executor.submit(self.cpu_collector.collect)
        future_mem = self._executor.submit(self.memory_collector.collect)
        future_disk = self._executor.submit(self.disk_collector.collect)
        future_net = self._executor.submit(self.network_collector.collect)

        cpu_data = future_cpu.result(timeout=2.0)
        mem_data = future_mem.result(timeout=2.0)
        disk_data = future_disk.result(timeout=2.0)
        net_data = future_net.result(timeout=2.0)

        # Merge into unified snapshot
        unified = {
            "timestamp": cpu_data["timestamp"],
            # CPU
            "cpu_percent": cpu_data["cpu_percent"],
            "per_core": cpu_data["per_core"],
            "freq_current": cpu_data["freq_current"],
            "freq_min": cpu_data["freq_min"],
            "freq_max": cpu_data["freq_max"],
            "cpu_times": cpu_data["cpu_times"],
            # Memory
            "memory_total": mem_data["memory_total"],
            "memory_used": mem_data["memory_used"],
            "memory_available": mem_data["memory_available"],
            "memory_percent": mem_data["memory_percent"],
            "swap_total": mem_data["swap_total"],
            "swap_used": mem_data["swap_used"],
            "swap_percent": mem_data["swap_percent"],
            "memory_pressure": mem_data["memory_pressure"],
            # Disk
            "total_storage": disk_data["total_storage"],
            "used_storage": disk_data["used_storage"],
            "free_storage": disk_data["free_storage"],
            "disk_percent": disk_data["disk_percent"],
            "disk_read_bytes": disk_data["disk_read_bytes"],
            "disk_write_bytes": disk_data["disk_write_bytes"],
            "read_bytes_per_sec": disk_data["read_bytes_per_sec"],
            "write_bytes_per_sec": disk_data["write_bytes_per_sec"],
            "read_iops": disk_data["read_iops"],
            "write_iops": disk_data["write_iops"],
            "partitions": disk_data["partitions"],
            # Network
            "network_sent_bytes": net_data["bytes_sent"],
            "network_received_bytes": net_data["bytes_recv"],
            "packets_sent": net_data["packets_sent"],
            "packets_recv": net_data["packets_recv"],
            "upload_speed": net_data["upload_speed"],
            "download_speed": net_data["download_speed"],
            "interfaces": net_data["interfaces"],
        }
        return unified

    def _run_loop(self) -> None:
        """Main loop executed inside the background daemon thread."""
        logger.info("MonitoringEngine background execution loop started.")

        # Track process collection task
        self._process_future = None
        self._last_process_dispatch_time = 0.0

        while not self._stop_event.is_set():
            loop_start = time.perf_counter()

            try:
                proc_res = None
                # 1. Collect Core Unified Metrics (Non-blocking, fast)
                unified_metrics = self._collect_unified_metrics()

                # 2. Check and harvest completed asynchronous process collection
                if self._process_future is not None and self._process_future.done():
                    try:
                        proc_res = self._process_future.result()
                        with self._lock:
                            self._latest_processes = proc_res
                    except Exception as pe:
                        logger.warning("Error harvesting process scan: %s", pe)
                    self._process_future = None

                # Dispatch next process collection if due and not already running
                now = time.time()
                if (now - self._last_process_dispatch_time >= self.process_sampling_interval) and (self._process_future is None):
                    self._last_process_dispatch_time = now
                    self._process_future = self._executor.submit(self.process_collector.collect)

                # 3. Update thread-safe shared states
                with self._lock:
                    self._latest_metrics = unified_metrics
                    self._recent_metrics.append(unified_metrics)
                    listeners = list(self._listeners)

                # 4. Background Persistence & Alert Evaluation
                try:
                    if self.db_manager:
                        self.db_manager.insert_system_metric(unified_metrics)
                        if proc_res is not None:
                            top_to_persist = proc_res.get("top_cpu", []) + proc_res.get("top_memory", [])
                            self.db_manager.insert_process_snapshots(now, top_to_persist)

                    if self.alert_manager:
                        self.alert_manager.check_metrics(unified_metrics)
                except Exception as de:
                    logger.debug("Database / Alert background hook: %s", de)

                # 5. Notify Registered Listeners outside lock
                for listener in listeners:
                    try:
                        listener(unified_metrics)
                    except Exception as le:
                        logger.error("Error in listener callback: %s", le)

            except Exception as e:
                logger.error("Unexpected error in monitoring cycle: %s", e, exc_info=True)

            # Sleep precision accounting for execution time
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0.02, self.sampling_interval - elapsed)

            # Interruptible sleep using stop_event.wait
            if self._stop_event.wait(timeout=sleep_time):
                break

        logger.info("MonitoringEngine loop terminated cleanly.")

    # --- Thread-Safe Query API for Dashboard & Analytics ---

    def get_latest_metrics(self) -> Dict[str, Any]:
        """Returns a snapshot copy of the most recent resource metrics."""
        with self._lock:
            return dict(self._latest_metrics)

    def get_recent_history(self) -> List[Dict[str, Any]]:
        """Returns a list copy of recent metric snapshots in the in-memory circular buffer."""
        with self._lock:
            return list(self._recent_metrics)

    def get_latest_processes(self) -> Dict[str, Any]:
        """Returns a copy of the latest process snapshot and top consumers."""
        with self._lock:
            return dict(self._latest_processes)

    def trigger_single_collection(self) -> Dict[str, Any]:
        """
        Manually triggers a single collection cycle synchronously.
        Updates in-memory state, persists to SQLite, and evaluates alerts.
        """
        unified = self._collect_unified_metrics()
        proc_data = self.process_collector.collect()
        now = unified.get("timestamp", time.time())

        with self._lock:
            self._latest_metrics = unified
            self._recent_metrics.append(unified)
            self._latest_processes = proc_data

        try:
            if self.db_manager:
                self.db_manager.insert_system_metric(unified)
                if proc_data:
                    top_to_persist = proc_data.get("top_cpu", []) + proc_data.get("top_memory", [])
                    self.db_manager.insert_process_snapshots(now, top_to_persist)
            if self.alert_manager:
                self.alert_manager.check_metrics(unified)
        except Exception as e:
            logger.debug("Manual snapshot persistence error: %s", e)

        return unified
