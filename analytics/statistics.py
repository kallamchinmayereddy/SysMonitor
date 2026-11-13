"""
SysMonitor Performance Statistics Utility
Calculates rolling averages, peaks, standard deviations, and resource utilization summaries.
"""
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd


def calculate_series_stats(series: Union[List[float], pd.Series, np.ndarray]) -> Dict[str, float]:
    """
    Computes summary statistics for a resource utilization series.
    Returns current, mean, min, max, std, and 95th percentile.
    """
    if series is None or len(series) == 0:
        return {
            "current": 0.0,
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std": 0.0,
            "p95": 0.0,
        }

    arr = np.array(series, dtype=float)
    # Remove NaNs if any
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {"current": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0, "p95": 0.0}

    return {
        "current": round(float(arr[-1]), 1),
        "mean": round(float(np.mean(arr)), 1),
        "min": round(float(np.min(arr)), 1),
        "max": round(float(np.max(arr)), 1),
        "std": round(float(np.std(arr)), 1),
        "p95": round(float(np.percentile(arr, 95)), 1),
    }


def summarize_metrics_dataframe(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Computes statistical profiles for key system metrics across a DataFrame.
    """
    if df.empty:
        return {}

    summary = {}
    target_cols = [
        "cpu_percent",
        "memory_percent",
        "disk_percent",
        "upload_speed",
        "download_speed",
        "read_bytes_per_sec",
        "write_bytes_per_sec",
    ]

    for col in target_cols:
        if col in df.columns:
            summary[col] = calculate_series_stats(df[col].dropna())

    return summary
