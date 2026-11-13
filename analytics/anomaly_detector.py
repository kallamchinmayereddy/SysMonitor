"""
SysMonitor Statistical Anomaly Detection Engine
Implements an explainable rolling Z-score statistical anomaly detection mechanism.
Compares real-time metrics against an adaptive historical baseline.
"""
from collections import deque
import time
from typing import Any, Dict, List, Optional
import numpy as np
from config.settings import (
    ANOMALY_BASELINE_MIN_SAMPLES,
    ANOMALY_WINDOW_SIZE,
    ANOMALY_ZSCORE_THRESHOLD,
)
from utils.logger import get_logger

logger = get_logger("AnomalyDetector")


class AnomalyDetector:
    """
    Detects statistical anomalies using rolling mean and standard deviation (Z-Score).
    Strictly statistical and fully explainable without black-box ML claims.
    """

    def __init__(
        self,
        window_size: int = ANOMALY_WINDOW_SIZE,
        min_samples: int = ANOMALY_BASELINE_MIN_SAMPLES,
        z_threshold: float = ANOMALY_ZSCORE_THRESHOLD,
    ):
        self.window_size = window_size
        self.min_samples = min_samples
        self.z_threshold = z_threshold

        # Rolling buffers per tracked metric
        self._buffers: Dict[str, deque] = {
            "cpu_percent": deque(maxlen=self.window_size),
            "memory_percent": deque(maxlen=self.window_size),
            "read_bytes_per_sec": deque(maxlen=self.window_size),
            "write_bytes_per_sec": deque(maxlen=self.window_size),
            "download_speed": deque(maxlen=self.window_size),
            "upload_speed": deque(maxlen=self.window_size),
        }
        logger.debug("AnomalyDetector initialized (Window: %d, MinSamples: %d, Z-Threshold: %.1f)",
                     window_size, min_samples, z_threshold)

    def evaluate_metric(
        self,
        metric_name: str,
        value: float,
        timestamp: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates a single metric value against its rolling historical baseline.
        Returns an anomaly payload if statistically anomalous, else None.
        """
        if metric_name not in self._buffers:
            self._buffers[metric_name] = deque(maxlen=self.window_size)

        buf = self._buffers[metric_name]

        # Check if baseline has enough samples
        if len(buf) < self.min_samples:
            buf.append(value)
            return None

        # Calculate baseline statistics
        baseline = np.array(buf, dtype=float)
        mean = float(np.mean(baseline))
        std = float(np.std(baseline))

        # Avoid zero or near-zero division for static metrics
        effective_std = max(std, 2.0)

        # Compute Z-score
        z_score = (value - mean) / effective_std

        # Append current value to buffer
        buf.append(value)

        # Positive statistical deviation exceeding threshold
        if z_score >= self.z_threshold:
            reason = (
                f"{metric_name.replace('_', ' ').title()} spiked to {value:.1f}, "
                f"which is +{z_score:.2f}σ above recent baseline ({mean:.1f} ± {std:.1f})"
            )
            logger.info("Statistical Anomaly Detected: %s", reason)
            return {
                "timestamp": timestamp or time.time(),
                "metric_name": metric_name,
                "observed_value": round(value, 2),
                "baseline_mean": round(mean, 2),
                "baseline_std": round(std, 2),
                "z_score": round(z_score, 2),
                "threshold": self.z_threshold,
                "reason": reason,
            }

        return None

    def evaluate_snapshot(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluates all supported metrics in a system snapshot.
        Returns a list of detected anomalies (if any).
        """
        anomalies = []
        now = metrics.get("timestamp", time.time())

        for key in ["cpu_percent", "memory_percent", "read_bytes_per_sec", "write_bytes_per_sec", "download_speed"]:
            if key in metrics and metrics[key] is not None:
                anomaly = self.evaluate_metric(key, float(metrics[key]), timestamp=now)
                if anomaly:
                    anomalies.append(anomaly)

        return anomalies
