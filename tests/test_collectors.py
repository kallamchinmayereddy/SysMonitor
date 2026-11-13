"""
SysMonitor Unit Test Suite - Collectors & Monitoring Engine
Tests real metrics retrieval, differential rate calculations, thread safety,
and background engine lifecycle controls.
"""
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from collector.cpu_collector import CPUCollector
from collector.memory_collector import MemoryCollector
from collector.disk_collector import DiskCollector
from collector.network_collector import NetworkCollector
from collector.process_collector import ProcessCollector
from collector.monitoring_engine import MonitoringEngine


class TestCPUCollector:
    """Tests for CPUCollector metrics acquisition."""

    def test_cpu_collection_structure_and_ranges(self):
        collector = CPUCollector()
        time.sleep(0.1)
        data = collector.collect()

        assert "cpu_percent" in data
        assert isinstance(data["cpu_percent"], float)
        assert 0.0 <= data["cpu_percent"] <= 100.0

        assert "per_core" in data
        assert isinstance(data["per_core"], list)
        assert len(data["per_core"]) == data["logical_cores"]
        assert data["logical_cores"] >= 1
        assert data["physical_cores"] >= 1

        assert "cpu_times" in data
        assert "user" in data["cpu_times"]
        assert "system" in data["cpu_times"]
        assert "idle" in data["cpu_times"]


class TestMemoryCollector:
    """Tests for MemoryCollector metrics acquisition."""

    def test_memory_collection_structure_and_pressure(self):
        collector = MemoryCollector()
        data = collector.collect()

        assert data["memory_total"] > 0
        assert data["memory_available"] > 0
        assert data["memory_used"] > 0
        assert 0.0 <= data["memory_percent"] <= 100.0
        assert data["memory_pressure"] in ["Normal", "Moderate", "High", "Critical"]
        assert data["swap_total"] >= 0
        assert 0.0 <= data["swap_percent"] <= 100.0


class TestDiskCollector:
    """Tests for DiskCollector storage and I/O rate differential."""

    def test_disk_collection_and_rates(self):
        collector = DiskCollector()
        time.sleep(0.2)
        data = collector.collect()

        assert "partitions" in data
        assert len(data["partitions"]) >= 1
        assert data["total_storage"] > 0
        assert 0.0 <= data["disk_percent"] <= 100.0

        assert data["read_bytes_per_sec"] >= 0.0
        assert data["write_bytes_per_sec"] >= 0.0
        assert data["read_iops"] >= 0.0
        assert data["write_iops"] >= 0.0


class TestNetworkCollector:
    """Tests for NetworkCollector interface inspection and speed calculation."""

    def test_network_collection_and_speeds(self):
        collector = NetworkCollector()
        time.sleep(0.2)
        data = collector.collect()

        assert data["bytes_sent"] >= 0
        assert data["bytes_recv"] >= 0
        assert data["packets_sent"] >= 0
        assert data["packets_recv"] >= 0
        assert data["upload_speed"] >= 0.0
        assert data["download_speed"] >= 0.0
        assert isinstance(data["interfaces"], list)


class TestProcessCollector:
    """Tests for ProcessCollector scanning, top consumer identification, and filtering."""

    def test_process_collection(self):
        collector = ProcessCollector()
        data = collector.collect()

        assert data["total_processes"] > 0
        assert len(data["processes"]) > 0

        # Top 5 CPU
        assert len(data["top_cpu"]) <= 5
        if len(data["top_cpu"]) >= 2:
            assert data["top_cpu"][0]["cpu_percent"] >= data["top_cpu"][1]["cpu_percent"]

        # Top 5 Memory
        assert len(data["top_memory"]) <= 5
        if len(data["top_memory"]) >= 2:
            assert data["top_memory"][0]["memory_mb"] >= data["top_memory"][1]["memory_mb"]

    def test_process_filtering(self):
        sample = [
            {"pid": 100, "name": "python.exe", "cpu_percent": 12.0, "memory_mb": 150.0, "username": "user"},
            {"pid": 200, "name": "chrome.exe", "cpu_percent": 35.0, "memory_mb": 600.0, "username": "user"},
            {"pid": 300, "name": "code.exe", "cpu_percent": 5.0, "memory_mb": 400.0, "username": "user"},
        ]

        # Search filter
        filtered = ProcessCollector.filter_processes(sample, search_query="python")
        assert len(filtered) == 1
        assert filtered[0]["name"] == "python.exe"

        # Sort by CPU descending
        sorted_cpu = ProcessCollector.filter_processes(sample, sort_by="cpu_percent", ascending=False)
        assert sorted_cpu[0]["name"] == "chrome.exe"
        assert sorted_cpu[-1]["name"] == "code.exe"

        # Limit
        limited = ProcessCollector.filter_processes(sample, limit=2)
        assert len(limited) == 2


class TestMonitoringEngine:
    """Tests for MonitoringEngine singleton, background threading, and lifecycle controls."""

    def test_engine_singleton(self):
        engine1 = MonitoringEngine.get_instance()
        engine2 = MonitoringEngine.get_instance()
        assert engine1 is engine2

    def test_trigger_single_collection(self):
        engine = MonitoringEngine.get_instance()
        metrics = engine.trigger_single_collection()

        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert "disk_percent" in metrics
        assert "download_speed" in metrics

        latest = engine.get_latest_metrics()
        assert latest["cpu_percent"] == metrics["cpu_percent"]

        history = engine.get_recent_history()
        assert len(history) >= 1

        procs = engine.get_latest_processes()
        assert "top_cpu" in procs

    def test_background_lifecycle_and_listeners(self):
        engine = MonitoringEngine.get_instance()

        received_snapshots = []

        def listener(snapshot):
            received_snapshots.append(snapshot)

        engine.add_listener(listener)

        # Start background loop with fast interval for testing
        started = engine.start(sampling_interval=0.2)
        assert started or engine.is_running()
        assert engine.is_running() is True

        # Duplicate start should be ignored safely
        duplicate_start = engine.start()
        assert duplicate_start is False

        # Allow worker thread to run for 3-4 cycles
        time.sleep(1.0)

        # Stop background loop
        stopped = engine.stop()
        assert stopped is True
        assert engine.is_running() is False

        # Cleanup listener
        engine.remove_listener(listener)

        # Verify listener received multiple snapshots
        assert len(received_snapshots) >= 2
        assert "cpu_percent" in received_snapshots[0]
