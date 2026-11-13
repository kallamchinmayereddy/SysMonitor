"""
SysMonitor Unit Test Suite - Alert Management
Tests threshold triggers, cooldown deduplication, and alert persistence.
"""
from pathlib import Path
import sys
import tempfile
import time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from alerts.alert_manager import AlertManager
from database.db_manager import DatabaseManager


@pytest.fixture
def test_alert_manager():
    """Provides an AlertManager configured with an isolated test SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_alerts.db"
        db = DatabaseManager(db_path=db_path)
        mgr = AlertManager(
            db_manager=db,
            cpu_warn=70.0,
            cpu_crit=90.0,
            mem_warn=80.0,
            mem_crit=95.0,
            cooldown_seconds=10.0,
        )
        yield mgr


class TestAlertManager:
    """Tests for threshold alert handling and cooldown logic."""

    def test_cpu_warning_and_critical(self, test_alert_manager):
        now = time.time()

        # Warning trigger
        alerts = test_alert_manager.check_metrics({
            "timestamp": now,
            "cpu_percent": 75.0,
            "memory_percent": 50.0,
            "disk_percent": 40.0,
        })
        assert len(alerts) == 1
        assert alerts[0]["type"] == "CPU"
        assert alerts[0]["severity"] == "Warning"

        # Cooldown prevents immediate re-trigger
        alerts_cooldown = test_alert_manager.check_metrics({
            "timestamp": now + 2,
            "cpu_percent": 76.0,
            "memory_percent": 50.0,
            "disk_percent": 40.0,
        })
        assert len(alerts_cooldown) == 0

        # Critical threshold triggers as separate key
        alerts_crit = test_alert_manager.check_metrics({
            "timestamp": now + 4,
            "cpu_percent": 92.0,
            "memory_percent": 50.0,
            "disk_percent": 40.0,
        })
        assert len(alerts_crit) == 1
        assert alerts_crit[0]["severity"] == "Critical"

    def test_alert_persistence_in_db(self, test_alert_manager):
        now = time.time()
        test_alert_manager.check_metrics({
            "timestamp": now,
            "cpu_percent": 20.0,
            "memory_percent": 85.0,  # Triggers Memory Warning
            "disk_percent": 30.0,
        })
        db_alerts = test_alert_manager.db_manager.get_alerts()
        assert not db_alerts.empty
        assert db_alerts.iloc[0]["resource_type"] == "Memory"
