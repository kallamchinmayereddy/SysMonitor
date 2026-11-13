"""
SysMonitor Metric Formatting Utilities
Converts raw metrics into human-readable strings with appropriate units.
"""
from datetime import datetime, timezone
from typing import Union


def format_bytes(bytes_val: Union[int, float], precision: int = 2) -> str:
    """Converts a byte count into a human-readable string (B, KB, MB, GB, TB)."""
    if bytes_val is None:
        return "N/A"
    try:
        val = float(bytes_val)
    except (ValueError, TypeError):
        return "N/A"

    if val < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_idx = 0
    while val >= 1024.0 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1

    if unit_idx == 0:
        return f"{int(val)} B"
    return f"{val:.{precision}f} {units[unit_idx]}"


def format_rate(bytes_per_sec: Union[int, float], precision: int = 2) -> str:
    """Converts a byte transfer rate (bytes/s) to human-readable speed (e.g. 1.25 MB/s)."""
    if bytes_per_sec is None:
        return "0 B/s"
    formatted = format_bytes(bytes_per_sec, precision=precision)
    return f"{formatted}/s"


def format_percent(val: Union[int, float], precision: int = 1) -> str:
    """Formats a percentage value."""
    if val is None:
        return "N/A"
    try:
        f_val = float(val)
        return f"{f_val:.{precision}f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_duration(seconds: Union[int, float]) -> str:
    """Converts a duration in seconds into 'Xd Xh Xm Xs' or 'Xh Xm Xs'."""
    if seconds is None or seconds < 0:
        return "0s"
    secs = int(seconds)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, s = divmod(rem, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def format_frequency(mhz: Union[int, float]) -> str:
    """Formats CPU frequency in MHz or GHz."""
    if mhz is None or mhz <= 0:
        return "N/A"
    if mhz >= 1000:
        return f"{mhz / 1000.0:.2f} GHz"
    return f"{mhz:.0f} MHz"


def format_timestamp(ts: Union[float, int, datetime, str]) -> str:
    """Standardizes timestamps into 'YYYY-MM-DD HH:MM:SS' format."""
    if ts is None:
        return "N/A"
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)
