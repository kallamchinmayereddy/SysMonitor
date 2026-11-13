"""
SysMonitor Thread-Safe Database Manager (SQLite)
Manages persistent storage, parameterized queries, historical range retrieval,
alert tracking, automated data pruning, and CSV exports.
"""
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from config.settings import DB_PATH, HISTORY_RETENTION_DAYS, PROCESS_SNAPSHOT_RETENTION_HOURS
from utils.logger import get_logger

logger = get_logger("DBManager")


class DatabaseManager:
    """Thread-safe SQLite manager for SysMonitor historical records."""

    _instance: Optional["DatabaseManager"] = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "DatabaseManager":
        """Singleton accessor for process-wide DatabaseManager."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls(db_path=db_path or DB_PATH)
            return cls._instance

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._schema_file = Path(__file__).resolve().parent / "schema.sql"

        self.init_db()
        logger.info("DatabaseManager initialized with database: %s", self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection configured with WAL mode and row factory."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def init_db(self) -> None:
        """Applies schema.sql to initialize database tables and indexes."""
        if not self._schema_file.exists():
            raise FileNotFoundError(f"Schema file not found at {self._schema_file}")

        with open(self._schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with self._write_lock:
            with self._get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
        logger.debug("Database schema initialized and verified.")

    # --- System Metrics Persistence ---

    def insert_system_metric(self, m: Dict[str, Any]) -> int:
        """Inserts a single unified system metric record."""
        query = """
        INSERT INTO system_metrics (
            timestamp, cpu_percent, memory_percent, memory_used, memory_available,
            disk_percent, disk_read_bytes, disk_write_bytes, read_bytes_per_sec,
            write_bytes_per_sec, network_sent_bytes, network_received_bytes,
            upload_speed, download_speed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            m.get("timestamp", time.time()),
            float(m.get("cpu_percent", 0.0)),
            float(m.get("memory_percent", 0.0)),
            int(m.get("memory_used", 0)),
            int(m.get("memory_available", 0)),
            float(m.get("disk_percent", 0.0)),
            int(m.get("disk_read_bytes", 0)),
            int(m.get("disk_write_bytes", 0)),
            float(m.get("read_bytes_per_sec", 0.0)),
            float(m.get("write_bytes_per_sec", 0.0)),
            int(m.get("network_sent_bytes", 0)),
            int(m.get("network_received_bytes", 0)),
            float(m.get("upload_speed", 0.0)),
            float(m.get("download_speed", 0.0)),
        )

        with self._write_lock:
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.lastrowid

    def insert_process_snapshots(self, timestamp: float, processes: List[Dict[str, Any]]) -> int:
        """Batch inserts process snapshots (typically top consumers)."""
        if not processes:
            return 0

        query = """
        INSERT INTO process_snapshots (
            timestamp, pid, process_name, cpu_percent, memory_percent,
            memory_usage, num_threads, process_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                timestamp,
                int(p.get("pid", 0)),
                str(p.get("name", "Unknown")),
                float(p.get("cpu_percent", 0.0)),
                float(p.get("memory_percent", 0.0)),
                float(p.get("memory_mb", 0.0)),
                int(p.get("threads", 1)),
                str(p.get("status", "unknown")),
            )
            for p in processes
        ]

        with self._write_lock:
            with self._get_connection() as conn:
                conn.executemany(query, rows)
                conn.commit()
                return len(rows)

    def insert_alert_event(
        self,
        resource_type: str,
        severity: str,
        message: str,
        observed_value: float,
        threshold_value: float,
        timestamp: Optional[float] = None,
    ) -> int:
        """Inserts an alert event record."""
        query = """
        INSERT INTO alert_events (
            timestamp, resource_type, severity, message,
            observed_value, threshold_value, acknowledged
        ) VALUES (?, ?, ?, ?, ?, ?, 0)
        """
        params = (
            timestamp or time.time(),
            resource_type,
            severity,
            message,
            float(observed_value),
            float(threshold_value),
        )

        with self._write_lock:
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                logger.info("Alert persisted: [%s] %s (Observed: %.1f, Threshold: %.1f)",
                            severity, message, observed_value, threshold_value)
                return cursor.lastrowid

    # --- Query API ---

    def get_metrics_range(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = 5000,
    ) -> pd.DataFrame:
        """
        Retrieves historical system metrics within an epoch time window as a Pandas DataFrame.
        """
        clauses = []
        params: List[Any] = []

        if start_time is not None:
            clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time is not None:
            clauses.append("timestamp <= ?")
            params.append(end_time)

        where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_str = f"LIMIT {limit}" if limit else ""

        query = f"""
        SELECT * FROM system_metrics
        {where_str}
        ORDER BY timestamp ASC
        {limit_str}
        """

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if not df.empty and "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        return df

    def get_recent_metrics_df(self, limit: int = 120) -> pd.DataFrame:
        """Retrieves the latest N metric rows for immediate live charting."""
        query = f"""
        SELECT * FROM (
            SELECT * FROM system_metrics
            ORDER BY timestamp DESC
            LIMIT {limit}
        ) ORDER BY timestamp ASC
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        if not df.empty and "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        return df

    def get_alerts(
        self,
        unacknowledged_only: bool = False,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Retrieves system alert events."""
        where_clause = "WHERE acknowledged = 0" if unacknowledged_only else ""
        query = f"""
        SELECT * FROM alert_events
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        if not df.empty and "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        return df

    def get_unacknowledged_alert_count(self) -> int:
        """Counts pending unacknowledged alerts."""
        query = "SELECT COUNT(*) as count FROM alert_events WHERE acknowledged = 0"
        with self._get_connection() as conn:
            row = conn.execute(query).fetchone()
            return int(row["count"]) if row else 0

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Marks a specific alert as acknowledged."""
        query = "UPDATE alert_events SET acknowledged = 1 WHERE id = ?"
        with self._write_lock:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (alert_id,))
                conn.commit()
                return cursor.rowcount > 0

    def acknowledge_all_alerts(self) -> int:
        """Marks all unacknowledged alerts as acknowledged."""
        query = "UPDATE alert_events SET acknowledged = 1 WHERE acknowledged = 0"
        with self._write_lock:
            with self._get_connection() as conn:
                cursor = conn.execute(query)
                conn.commit()
                return cursor.rowcount

    # --- Maintenance & Pruning ---

    def prune_old_data(
        self,
        retention_days: int = HISTORY_RETENTION_DAYS,
        process_retention_hours: int = PROCESS_SNAPSHOT_RETENTION_HOURS,
    ) -> Dict[str, int]:
        """
        Purges historical metric and process snapshot records older than retention policies.
        Prevents unbounded database growth.
        """
        now = time.time()
        metrics_cutoff = now - (retention_days * 86400)
        process_cutoff = now - (process_retention_hours * 3600)

        with self._write_lock:
            with self._get_connection() as conn:
                c1 = conn.execute("DELETE FROM system_metrics WHERE timestamp < ?", (metrics_cutoff,))
                c2 = conn.execute("DELETE FROM process_snapshots WHERE timestamp < ?", (process_cutoff,))
                conn.commit()
                deleted_metrics = c1.rowcount
                deleted_procs = c2.rowcount

        logger.info("Pruned %d old system metrics and %d old process snapshots", deleted_metrics, deleted_procs)
        return {"pruned_metrics": deleted_metrics, "pruned_processes": deleted_procs}

    # --- Export Utilities ---

    def format_metrics_for_export(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms raw database metric records into an intuitive, human-readable
        report with clear column units, preventing scientific notation in Excel.
        """
        if df.empty:
            return df

        export_df = pd.DataFrame()

        # Readable Timestamp
        if "timestamp" in df.columns:
            export_df["Timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
        elif "datetime" in df.columns:
            export_df["Timestamp"] = pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        # CPU
        if "cpu_percent" in df.columns:
            export_df["CPU Usage (%)"] = df["cpu_percent"].round(1)

        # RAM in GB
        if "memory_percent" in df.columns:
            export_df["RAM Usage (%)"] = df["memory_percent"].round(1)
        if "memory_used" in df.columns:
            export_df["RAM Used (GB)"] = (df["memory_used"] / (1024**3)).round(2)
        if "memory_available" in df.columns:
            export_df["RAM Available (GB)"] = (df["memory_available"] / (1024**3)).round(2)

        # Storage
        if "disk_percent" in df.columns:
            export_df["Disk Storage Used (%)"] = df["disk_percent"].round(1)

        # Disk I/O Rates (MB/s)
        if "read_bytes_per_sec" in df.columns:
            export_df["Disk Read (MB/s)"] = (df["read_bytes_per_sec"] / (1024**2)).round(2)
        if "write_bytes_per_sec" in df.columns:
            export_df["Disk Write (MB/s)"] = (df["write_bytes_per_sec"] / (1024**2)).round(2)

        # Network Throughput (KB/s)
        if "download_speed" in df.columns:
            export_df["Download Speed (KB/s)"] = (df["download_speed"] / 1024.0).round(2)
        if "upload_speed" in df.columns:
            export_df["Upload Speed (KB/s)"] = (df["upload_speed"] / 1024.0).round(2)

        # Total Network Volume (MB)
        if "network_received_bytes" in df.columns:
            export_df["Total Net Recv (MB)"] = (df["network_received_bytes"] / (1024**2)).round(2)
        if "network_sent_bytes" in df.columns:
            export_df["Total Net Sent (MB)"] = (df["network_sent_bytes"] / (1024**2)).round(2)

        return export_df

    def export_metrics_csv(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> str:
        """Exports human-readable historical metrics to CSV formatted text."""
        df = self.get_metrics_range(start_time, end_time, limit=None)
        if df.empty:
            return ""
        formatted_df = self.format_metrics_for_export(df)
        return formatted_df.to_csv(index=False)

    def export_alerts_csv(self) -> str:
        """Exports all alerts to a human-readable CSV formatted text."""
        df = self.get_alerts(limit=5000)
        if df.empty:
            return ""
        
        export_df = pd.DataFrame()
        export_df["Alert ID"] = df["id"]
        export_df["Timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
        export_df["Severity"] = df["severity"]
        export_df["Resource"] = df["resource_type"]
        export_df["Message"] = df["message"]
        export_df["Observed Value"] = df["observed_value"].round(1)
        export_df["Threshold Limit"] = df["threshold_value"].round(1)
        export_df["Status"] = df["acknowledged"].apply(lambda a: "Acknowledged" if a else "Active")

        return export_df.to_csv(index=False)
