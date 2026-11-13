"""
SysMonitor Global Configuration Settings
Defines operational parameters, paths, thresholds, and defaults.
"""
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Database & Log File Paths
DB_PATH = DATA_DIR / "sysmonitor.db"
LOG_FILE = LOGS_DIR / "sysmonitor.log"

# Monitoring Engine Configuration
APP_NAME = "SysMonitor"
APP_VERSION = "1.0.0"
DEFAULT_SAMPLING_INTERVAL = 1.0  # seconds
PROCESS_SAMPLING_INTERVAL = 2.0  # process scans are slightly heavier, throttled to 2s
RECENT_BUFFER_MAXLEN = 120       # in-memory circular buffer size for live charts

# Default Alert Thresholds (percentages)
CPU_WARNING_THRESHOLD = 80.0
CPU_CRITICAL_THRESHOLD = 90.0
MEMORY_WARNING_THRESHOLD = 85.0
MEMORY_CRITICAL_THRESHOLD = 95.0
DISK_WARNING_THRESHOLD = 85.0
DISK_CRITICAL_THRESHOLD = 92.0

# Alert Management
ALERT_COOLDOWN_SECONDS = 60  # minimum seconds between alerts of the same type/severity

# Anomaly Detection Defaults (Rolling Z-Score)
ANOMALY_BASELINE_MIN_SAMPLES = 20
ANOMALY_WINDOW_SIZE = 40
ANOMALY_ZSCORE_THRESHOLD = 2.5

# Health Score Calculation Weights (Heuristic 0-100)
HEALTH_WEIGHT_CPU = 0.40
HEALTH_WEIGHT_MEM = 0.40
HEALTH_WEIGHT_DISK = 0.20

# Historical Retention
HISTORY_RETENTION_DAYS = 7
PROCESS_SNAPSHOT_RETENTION_HOURS = 24
