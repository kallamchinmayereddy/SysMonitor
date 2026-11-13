"""
SysMonitor Unit Test Suite - Database Persistence Layer
Tests SQLite schema initialization, thread safety, metric insertion,
historical range queries, alert acknowledgments, and data pruning.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from database.db_manager import DatabaseManager


@pytest.fixture
def temp_db():
    """Provides a fresh isolated database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_sysmonitor.db"
        manager = DatabaseManager(db_path=db_path)
        yield manager


class TestDatabaseManager:
    """Tests for SQLite persistence operations."""

    def test_schema_initialization(self, temp_db):
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]
        assert "system_metrics" in tables
        assert "process_snapshots" in tables
        assert "alert_events" in tables
        conn.close()

    def test_insert_and_query_metrics(self, temp_db):
        now = time.time()
        metric = {
            "timestamp": now,
            "cpu_percent": 45.5,
            "memory_percent": 68.2,
            "memory_used": 10000000000,
            "memory_available": 6000000000,
            "disk_percent": 55.0,
            "disk_read_bytes": 1024000,
            "disk_write_bytes": 2048000,
            "read_bytes_per_sec": 51200.0,
            "write_bytes_per_sec": 102400.0,
            "network_sent_bytes": 500000,
            "network_received_bytes": 1500000,
            "upload_speed": 1024.0,
            "download_speed": 2048.0,
        }

        row_id = temp_db.insert_system_metric(metric)
        assert row_id > 0

        # Query range
        df = temp_db.get_metrics_range(start_time=now - 10, end_time=now + 10)
        assert not df.empty
        assert len(df) == 1
        assert df.iloc[0]["cpu_percent"] == 45.5
        assert df.iloc[0]["download_speed"] == 2048.0

    def test_insert_and_query_processes(self, temp_db):
        now = time.time()
        procs = [
            {"pid": 101, "name": "python.exe", "cpu_percent": 15.0, "memory_percent": 3.2, "memory_mb": 250.0, "threads": 4, "status": "running"},
            {"pid": 102, "name": "code.exe", "cpu_percent": 8.0, "memory_percent": 5.1, "memory_mb": 420.0, "threads": 12, "status": "running"},
        ]
        count = temp_db.insert_process_snapshots(now, procs)
        assert count == 2

    def test_alerts_lifecycle(self, temp_db):
        now = time.time()
        # Insert 2 alerts
        id1 = temp_db.insert_alert_event(
            resource_type="CPU",
            severity="Warning",
            message="CPU utilization at 82%",
            observed_value=82.0,
            threshold_value=80.0,
            timestamp=now - 5,
        )
        id2 = temp_db.insert_alert_event(
            resource_type="Memory",
            severity="Critical",
            message="RAM utilization at 96%",
            observed_value=96.0,
            threshold_value=95.0,
            timestamp=now,
        )

        assert id1 > 0 and id2 > 0
        assert temp_db.get_unacknowledged_alert_count() == 2

        # Acknowledge single
        assert temp_db.acknowledge_alert(id1) is True
        assert temp_db.get_unacknowledged_alert_count() == 1

        # Acknowledge all
        ack_count = temp_db.acknowledge_all_alerts()
        assert ack_count == 1
        assert temp_db.get_unacknowledged_alert_count() == 0

    def test_data_pruning(self, temp_db):
        now = time.time()
        old_time = now - (10 * 86400)  # 10 days ago

        # Insert old metric
        temp_db.insert_system_metric({
            "timestamp": old_time,
            "cpu_percent": 20.0,
            "memory_percent": 30.0,
            "memory_used": 1000,
            "memory_available": 1000,
            "disk_percent": 10.0,
            "disk_read_bytes": 0,
            "disk_write_bytes": 0,
            "network_sent_bytes": 0,
            "network_received_bytes": 0,
        })

        # Insert fresh metric
        temp_db.insert_system_metric({
            "timestamp": now,
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "memory_used": 2000,
            "memory_available": 2000,
            "disk_percent": 20.0,
            "disk_read_bytes": 0,
            "disk_write_bytes": 0,
            "network_sent_bytes": 0,
            "network_received_bytes": 0,
        })

        res = temp_db.prune_old_data(retention_days=7, process_retention_hours=24)
        assert res["pruned_metrics"] == 1

        # Only fresh metric remains
        remaining = temp_db.get_metrics_range()
        assert len(remaining) == 1
        assert remaining.iloc[0]["cpu_percent"] == 50.0

    def test_csv_export(self, temp_db):
        now = time.time()
        temp_db.insert_system_metric({
            "timestamp": now,
            "cpu_percent": 33.3,
            "memory_percent": 44.4,
            "memory_used": 500,
            "memory_available": 500,
            "disk_percent": 22.2,
            "disk_read_bytes": 0,
            "disk_write_bytes": 0,
            "network_sent_bytes": 0,
            "network_received_bytes": 0,
        })
        csv_str = temp_db.export_metrics_csv()
        assert "CPU Usage (%)" in csv_str
        assert "RAM Used (GB)" in csv_str
        assert "33.3" in csv_str

    def test_concurrent_writes(self, temp_db):
        """Tests that multiple threads can insert concurrently without SQLite locking failures."""
        now = time.time()

        def worker(idx):
            for i in range(20):
                temp_db.insert_system_metric({
                    "timestamp": now + (idx * 100) + i,
                    "cpu_percent": float(i),
                    "memory_percent": float(i),
                    "memory_used": i * 1000,
                    "memory_available": i * 1000,
                    "disk_percent": 10.0,
                    "disk_read_bytes": 0,
                    "disk_write_bytes": 0,
                    "network_sent_bytes": 0,
                    "network_received_bytes": 0,
                })

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(worker, idx) for idx in range(5)]
            for f in futures:
                f.result()

        df = temp_db.get_metrics_range(limit=None)
        assert len(df) == 100
