"""
SysMonitor Unit Test Suite - Analytics & Intelligence Layer
Tests rolling statistics calculations, explainable anomaly detection,
and heuristic system health scoring.
"""
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import pytest
from analytics.statistics import calculate_series_stats, summarize_metrics_dataframe
from analytics.anomaly_detector import AnomalyDetector
from analytics.health_score import HealthScoreCalculator


class TestStatistics:
    """Tests for statistical aggregation."""

    def test_calculate_series_stats(self):
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = calculate_series_stats(data)
        assert stats["current"] == 50.0
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["p95"] >= 45.0

    def test_empty_series_stats(self):
        stats = calculate_series_stats([])
        assert stats["mean"] == 0.0

    def test_summarize_dataframe(self):
        df = pd.DataFrame({
            "cpu_percent": [10.0, 20.0, 30.0],
            "memory_percent": [50.0, 60.0, 70.0],
        })
        summary = summarize_metrics_dataframe(df)
        assert "cpu_percent" in summary
        assert summary["cpu_percent"]["mean"] == 20.0
        assert summary["memory_percent"]["mean"] == 60.0


class TestAnomalyDetector:
    """Tests for rolling Z-score statistical anomaly detection."""

    def test_baseline_calibration(self):
        detector = AnomalyDetector(min_samples=20)
        # First 19 samples should return None (calibrating baseline)
        for i in range(19):
            res = detector.evaluate_metric("cpu_percent", 15.0)
            assert res is None

    def test_anomaly_detection_and_explanation(self):
        detector = AnomalyDetector(min_samples=20, z_threshold=2.5)
        # Establish stable baseline around 10%
        for i in range(25):
            detector.evaluate_metric("cpu_percent", 10.0 + (i % 3))

        # Normal value within baseline
        normal_res = detector.evaluate_metric("cpu_percent", 12.0)
        assert normal_res is None

        # Massive sudden spike
        spike_res = detector.evaluate_metric("cpu_percent", 85.0)
        assert spike_res is not None
        assert spike_res["observed_value"] == 85.0
        assert spike_res["z_score"] >= 2.5
        assert "spiked" in spike_res["reason"]


class TestHealthScoreCalculator:
    """Tests for explainable health score evaluation."""

    def test_optimal_health(self):
        calc = HealthScoreCalculator()
        result = calc.calculate(cpu_percent=15.0, memory_percent=40.0, disk_percent=50.0)
        assert result["score"] == 100.0
        assert result["category"] == "Optimal"
        assert result["penalties"]["cpu"] == 0.0
        assert result["penalties"]["memory"] == 0.0

    def test_critical_health(self):
        calc = HealthScoreCalculator()
        result = calc.calculate(cpu_percent=95.0, memory_percent=98.0, disk_percent=95.0)
        assert result["score"] < 50.0
        assert result["category"] == "Critical"
        assert len(result["reasons"]) >= 3
        assert len(result["recommendations"]) >= 3

    def test_degraded_health(self):
        calc = HealthScoreCalculator()
        result = calc.calculate(cpu_percent=75.0, memory_percent=75.0, disk_percent=60.0)
        assert 50.0 <= result["score"] < 85.0
        assert result["category"] in ["Good", "Degraded"]
