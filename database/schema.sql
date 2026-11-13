-- SysMonitor SQLite Relational Schema
-- Supports high-frequency metrics, process snapshots, and alert events

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- Table 1: Periodic Unified System Resource Metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    cpu_percent REAL NOT NULL,
    memory_percent REAL NOT NULL,
    memory_used INTEGER NOT NULL,
    memory_available INTEGER NOT NULL,
    disk_percent REAL NOT NULL,
    disk_read_bytes INTEGER NOT NULL,
    disk_write_bytes INTEGER NOT NULL,
    read_bytes_per_sec REAL NOT NULL DEFAULT 0.0,
    write_bytes_per_sec REAL NOT NULL DEFAULT 0.0,
    network_sent_bytes INTEGER NOT NULL,
    network_received_bytes INTEGER NOT NULL,
    upload_speed REAL NOT NULL DEFAULT 0.0,
    download_speed REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp);

-- Table 2: Top Process Snapshots
CREATE TABLE IF NOT EXISTS process_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    pid INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    cpu_percent REAL NOT NULL,
    memory_percent REAL NOT NULL,
    memory_usage REAL NOT NULL, -- Memory in MB
    num_threads INTEGER NOT NULL DEFAULT 1,
    process_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_proc_timestamp ON process_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_proc_cpu ON process_snapshots(cpu_percent);
CREATE INDEX IF NOT EXISTS idx_proc_name ON process_snapshots(process_name);

-- Table 3: System Alert Events
CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    resource_type TEXT NOT NULL,   -- 'CPU', 'Memory', 'Disk', 'Network', 'Anomaly'
    severity TEXT NOT NULL,        -- 'Warning', 'Critical', 'Info'
    message TEXT NOT NULL,
    observed_value REAL NOT NULL,
    threshold_value REAL NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0 -- 0=False, 1=True
);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alert_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alert_events(acknowledged);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alert_events(severity);
