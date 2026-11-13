# SysMonitor: Intelligent Real-Time System Resource Monitoring & Performance Analytics Platform

> **Academic Project**: 3rd-Year B.Tech Computer Science & Engineering – Operating Systems  
> **Author / Host**: Chinmaye Reddy  
> **Platform**: Windows 10/11 (with cross-platform POSIX abstraction)  
> **Language**: Python 3.10+  
> **Core Stack**: `psutil`, `Streamlit`, `Plotly`, `Pandas`, `NumPy`, `SQLite3`, `pytest`

---

## 1. Project Introduction

**SysMonitor** is an enterprise-grade, real-time operating system performance monitoring, telemetry analytics, and diagnostic platform designed for modern computer architectures. Unlike toy dashboards or simulated monitors, SysMonitor interfaces directly with the host kernel and hardware subsystem via standard OS system interfaces (`psutil`, Windows NT API, Windows Registry) to acquire genuine telemetry for CPU scheduling, virtual memory paging, disk I/O, network sockets, and kernel process table queues.

The system incorporates a background concurrent monitoring service, thread-safe Write-Ahead-Logging (WAL) SQLite persistence, explainable statistical anomaly detection ($Z$-score / standard deviation baselines), and a heuristic system health indicator (0–100) presented through an interactive, dark-themed Streamlit dashboard.

---

## 2. Problem Statement

Operating systems execute thousands of concurrent threads across multiple abstraction layers, often leading to performance degradation issues such as:
1. **CPU Saturation & Starvation**: Runaway processes monopolizing CPU time slices.
2. **Memory Leaks & Paging Thrashing**: Inefficient virtual memory allocation exhausting physical RAM and forcing excessive swap disk I/O.
3. **I/O Bottlenecks**: High-frequency disk read/write contention choking file system queues.
4. **Network Saturation**: Uncontrolled socket traffic saturating bandwidth.
5. **Lack of Historical Traceability**: Transient performance spikes occurring when an administrator is not actively watching.

Traditional operating system task managers provide ephemeral snapshots but lack historical time-series analytics, statistical anomaly classification, and unified diagnostic insights. **SysMonitor** addresses this problem by continuously recording system behavior into a persistent relational database and analyzing long-term usage trends.

---

## 3. Project Objectives

- **Continuous Low-Overhead Telemetry**: Background sampling without imposing more than negligible CPU load on the host.
- **Genuine Kernel & Hardware Introspection**: Zero simulated, dummy, or hardcoded metrics.
- **Modular Multithreaded Architecture**: Clear separation between collection, scheduling, persistence, analytics, and presentation.
- **Explainable Anomaly Detection**: Identifying statistical deviations based on rolling baseline standard deviations rather than arbitrary hard limits.
- **Historical Persistence & Export**: Storing time-stamped metrics into SQLite with pruning retention policies and CSV data export.
- **Educational Defense**: Demonstrating fundamental Operating Systems concepts for academic viva defense.

---

## 4. Key Features

| Module | Feature Capabilities |
|---|---|
| **CPU Monitoring** | Aggregate utilization %, per-core breakdown, clock frequency, user/system/idle execution times, 95th percentile, peak load. |
| **Memory Monitoring** | Physical RAM total/used/free/available, swap/paging utilization, automated memory pressure level calculation (`Normal`, `Moderate`, `High`, `Critical`). |
| **Disk Storage & I/O** | Mounted partition detection (`C:\`, `D:\`), capacity allocation, instantaneous read/write transfer rates (KB/s, MB/s via counter deltas), IOPS counters. |
| **Network Monitoring** | Active network adapters (Wi-Fi, Ethernet, WSL virtual adapters), link state, MTU, IP addresses, upload/download bandwidth speeds, packet drop/error tracking. |
| **Process Explorer** | Active kernel process enumeration, PID, status, thread counts, RSS memory (MB), CPU %, dynamic search, and multi-column sorting. |
| **Statistical Anomaly Detection** | Rolling Z-score engine ($Z \ge 2.5\sigma$) with adaptive sample baselines and clear natural language explanations for sudden spikes. |
| **System Health Score** | Explainable 0–100 heuristic index with weighted penalty models ($w_{cpu}=0.4, w_{mem}=0.4, w_{disk}=0.2$), observations, and actionable recommendations. |
| **Historical Analytics** | Time-range filtering (15m, 1h, 6h, 24h, 7d, custom date range), statistical aggregations, interactive Plotly charts, and CSV report export. |
| **Alert Management** | Configurable Warning & Critical thresholds, cooldown deduplication (prevents alert storms), interactive acknowledgment, and historical event logging. |

---

## 5. Technology Stack

- **Core Language**: Python 3 (Tested on 3.10.9)
- **Kernel & Telemetry Interfaces**: `psutil` (7.2.2), `winreg` (Windows Registry API)
- **Interactive UI & Presentation**: `Streamlit` (1.58.0)
- **Visualization**: `Plotly` (7.1.0)
- **Data Analysis**: `Pandas` (2.1.1), `NumPy` (1.26.4)
- **Database Engine**: `SQLite 3` with WAL mode (`PRAGMA journal_mode = WAL;`)
- **Concurrency & Multithreading**: `threading`, `concurrent.futures.ThreadPoolExecutor`, `threading.Lock`, `threading.Event`, `collections.deque`
- **Testing & Verification**: `pytest` (9.1.1)

---

## 6. System Architecture

SysMonitor is organized into decoupled architectural layers:

```
+-------------------------------------------------------------------------+
|                         PRESENTATION LAYER                              |
|   Streamlit Multi-Page UI | Custom Dark CSS Theme | Plotly Visuals      |
|   (Overview | CPU | Memory | Disk | Network | Process | History | Alert) |
+------------------------------------+------------------------------------+
                                     | (Reads buffered/queried telemetry)
+------------------------------------+------------------------------------+
|                         ANALYTICS LAYER                                 |
|   Statistics Summarizer | Anomaly Detector (Z-Score) | Health Calculator |
+------------------------------------+------------------------------------+
                                     |
+------------------------------------+------------------------------------+
|                    PERSISTENCE & ALERT LAYER                            |
|   Alert Manager (Cooldown) | SQLite Manager (WAL Mode, Retention Pruning)|
+------------------------------------+------------------------------------+
                                     | (Asynchronous batch writes)
+------------------------------------+------------------------------------+
|                       MONITORING ENGINE                                 |
|   Singleton Coordinator | Daemon Worker Thread | ThreadPoolExecutor     |
|   Thread-Safe Ring Buffer (deque) | threading.Lock Synchronization      |
+------------------------------------+------------------------------------+
                                     | (Concurrent I/O dispatch)
+------------------------------------+------------------------------------+
|                   DATA COLLECTION LAYER (psutil)                        |
|   CPUCollector | MemoryCollector | DiskCollector | Network | Process    |
+------------------------------------+------------------------------------+
                                     | (Kernel & Hardware Telemetry)
+------------------------------------+------------------------------------+
|                     HOST OPERATING SYSTEM & HARDWARE                    |
|   Windows NT Kernel / Registry / Disks / NICs / Task Scheduler          |
+-------------------------------------------------------------------------+
```

---

## 7. Folder Structure

```
SysMonitor/
├── app.py                      # Main Streamlit dashboard application
├── requirements.txt            # Dependency definitions
├── README.md                   # Full academic report and OS concepts guide
├── verify_phase1.py            # Phase 1 hardware verification script
├── config/
│   ├── __init__.py
│   └── settings.py             # Operational constants, paths, thresholds, intervals
├── collector/
│   ├── __init__.py
│   ├── cpu_collector.py        # CPU percent, per-core, frequency, execution times
│   ├── memory_collector.py     # Physical RAM, Swap, available, memory pressure
│   ├── disk_collector.py       # Partitions, usage, differential I/O rates (bytes/s)
│   ├── network_collector.py    # Interfaces, throughput rates (up/down bytes/s)
│   ├── process_collector.py    # Safe process scanning (PID, CPU, Mem, threads, user)
│   └── monitoring_engine.py    # Multithreaded collection coordinator (Singleton)
├── database/
│   ├── __init__.py
│   ├── schema.sql              # Relational schema with WAL mode & indexes
│   └── db_manager.py           # Thread-safe SQLite manager with retention pruning
├── analytics/
│   ├── __init__.py
│   ├── statistics.py           # Rolling averages, peak utilization, summary stats
│   ├── anomaly_detector.py     # Explainable rolling Z-score statistical detector
│   └── health_score.py         # Heuristic weighted health score (0–100) & diagnostics
├── alerts/
│   ├── __init__.py
│   └── alert_manager.py        # Threshold checker, cooldown deduplication, ack tracking
├── dashboard/
│   ├── __init__.py
│   ├── styles.py               # Dark-themed CSS, custom metric cards, Plotly layout
│   ├── overview.py             # System summary, live gauges, top processes, active alerts
│   ├── cpu_page.py             # CPU trends, per-core bar chart, kernel times
│   ├── memory_page.py          # RAM/Swap allocation breakdown, pressure warnings
│   ├── disk_page.py            # Partition capacity comparison, live I/O speed graph
│   ├── network_page.py         # Interfaces, upload/download throughput trends
│   ├── process_page.py         # Searchable, filterable process explorer with top 5
│   ├── history_page.py         # Time-range queries (15m, 1h, 6h, 24h, 7d), CSV export
│   └── alerts_page.py          # Active & historical alerts, acknowledgment controls
├── utils/
│   ├── __init__.py
│   ├── system_info.py          # Static hardware & OS identification (WinReg, Cores)
│   ├── formatters.py           # Unit formatters (B/KB/MB/GB, rates, %, durations)
│   └── logger.py               # Rotating file (logs/sysmonitor.log) and console logger
├── tests/
│   ├── __init__.py
│   ├── test_collectors.py      # Unit tests for collectors with live OS data
│   ├── test_database.py        # SQLite schema, concurrency, queries, pruning
│   ├── test_analytics.py       # Z-score anomaly detector, health score formulas
│   └── test_alerts.py          # Alert triggering, cooldown, and acknowledgment
├── data/
│   └── sysmonitor.db           # SQLite persistent storage database
└── logs/
    └── sysmonitor.log          # Rotating application execution log
```

---

## 8. Data Collection Methodology & Rate Mathematics

### Instantaneous Rate Calculations
Operating system counters for disk I/O and network transfer (e.g., `io.read_bytes`, `net_io.bytes_recv`) are monotonic cumulative counters since system boot. Directly reporting cumulative values does not reflect instantaneous load. SysMonitor computes transfer speed using exact high-resolution timestamps (`time.perf_counter()`):

$$\Delta t = t_{\text{current}} - t_{\text{previous}}$$

$$\text{Throughput Speed} = \frac{\text{Bytes}_{\text{current}} - \text{Bytes}_{\text{previous}}}{\Delta t} \quad [\text{Bytes/second}]$$

- **Counter Rollover / Reset Protection**: If $\Delta \text{Bytes} < 0$ (due to OS integer overflow or adapter reset), the delta is clamped to $0$ to prevent spurious spikes.

### Asynchronous Telemetry Decoupling
Lightweight hardware telemetry (CPU, RAM, Disk I/O, Network) executes within $<10\text{ ms}$. In contrast, enumerating hundreds of active processes with permissions checks takes $200\text{--}500\text{ ms}$. 
To prevent process enumeration from stalling high-frequency telemetry, the `MonitoringEngine` dispatches process table scans asynchronously using a `ThreadPoolExecutor` worker, ensuring the main metric loop ticks uninterrupted at its configured 1-second interval.

---

## 9. Database Relational Schema

SysMonitor uses SQLite 3 configured with **Write-Ahead Logging (WAL)** mode (`PRAGMA journal_mode = WAL;`) and normal synchronization (`PRAGMA synchronous = NORMAL;`) to support concurrent reads while background worker threads write telemetry.

```sql
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
    memory_usage REAL NOT NULL, -- MB
    num_threads INTEGER NOT NULL DEFAULT 1,
    process_status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_proc_timestamp ON process_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_proc_cpu ON process_snapshots(cpu_percent);

-- Table 3: System Alert Events
CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    resource_type TEXT NOT NULL,   -- 'CPU', 'Memory', 'Disk', 'Network', 'Anomaly'
    severity TEXT NOT NULL,        -- 'Warning', 'Critical'
    message TEXT NOT NULL,
    observed_value REAL NOT NULL,
    threshold_value REAL NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0 -- 0=False, 1=True
);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alert_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alert_events(acknowledged);
```

---

## 10. Operating Systems Concepts Demonstrated

This project serves as a comprehensive practical demonstration of third-year B.Tech Operating Systems principles:

1. **Process Management & Scheduling**:
   - Inspecting the kernel process control block (PCB) data: PID, process states (`RUNNING`, `SLEEPING`, `ZOMBIE`), thread count, creation time, and user ownership.
   - Understanding CPU scheduling time slices by tracking percentage CPU usage across cores over discrete intervals.
2. **CPU Utilization & Kernel vs. User Mode**:
   - Tracking time spent in user space (`cpu_times.user`) executing application instructions versus kernel space (`cpu_times.system`) servicing system calls and interrupt handling.
3. **Memory Management & Virtual Memory**:
   - Distinguishing resident physical RAM (`RSS`) from virtual address space.
   - Monitoring swap / paging file utilization to identify virtual memory page faults and memory thrashing.
4. **Storage & File System Management**:
   - Interfacing with mounted file system partitions (`NTFS` on Windows).
   - Distinguishing static file capacity from dynamic disk controller activity (I/O throughput in KB/s and IOPS).
5. **Concurrency & Thread Synchronization**:
   - **Singleton Pattern**: Ensuring exactly one monitoring coordinator exists across Streamlit UI re-runs.
   - **Race Condition Prevention**: Synchronizing shared buffer access using `threading.Lock`.
   - **Thread Pools**: Using `concurrent.futures.ThreadPoolExecutor` for concurrent sensor polling.
   - **Graceful Termination**: Coordinating daemon threads with `threading.Event` signaling without resource leaks.
6. **I/O Subsystems & Network Sockets**:
   - Aggregating network socket packet counters, detecting transmission drops/errors, and calculating instantaneous bandwidth.
7. **Resource Contention & Heuristic Health**:
   - Evaluating multi-resource penalties to compute holistic system stability scores and diagnostic troubleshooting recommendations.

---

## 11. Statistical Anomaly Detection & Health Scoring

### Anomaly Detection via Adaptive Rolling $Z$-Score
Rather than using arbitrary static thresholds, SysMonitor maintains a rolling circular buffer of the past $N=40$ readings ($t_{\text{baseline}} \ge 20\text{ samples}$) and calculates the sample mean $\mu$ and standard deviation $\sigma$:

$$Z = \frac{x_t - \mu}{\max(\sigma, 2.0)}$$

- A reading is flagged as a statistical anomaly if $Z \ge 2.5\sigma$.
- Every anomaly generates a natural-language explanation:  
  *e.g., "CPU percent spiked to 92.4%, which is +3.12σ above recent baseline (18.2% ± 12.1%)"*.

### System Health Score Heuristic (0–100)
The system calculates a heuristic stability score based on weighted penalties:

$$\text{Health Score} = 100 - (w_{\text{cpu}} \cdot P_{\text{cpu}} + w_{\text{mem}} \cdot P_{\text{mem}} + w_{\text{disk}} \cdot P_{\text{disk}})$$

Where $w_{\text{cpu}}=0.40, w_{\text{mem}}=0.40, w_{\text{disk}}=0.20$ and resource penalties scale from $0\%$ at safe baselines up to $100\%$ under saturation conditions.

---

## 12. Installation & Running Instructions

### Prerequisites
- Python 3.10+ (Standard Windows or Linux installation)
- `pip` package manager

### 1. Install Dependencies
```bash
cd "d:\OS Project"
pip install -r requirements.txt
```

### 2. Verify Hardware Probing (Phase 1 Probe)
Verify that your machine's hardware and OS metrics are recognized:
```bash
python verify_phase1.py
```

### 3. Launch the SysMonitor Interactive Dashboard
```bash
streamlit run app.py
```
The application will open in your default browser at `http://localhost:8501`.

---

## 13. Running the Test Suite

Run the full automated pytest suite covering collectors, database concurrency, anomaly detection, and alert management:

```bash
pytest tests/ -v
```

Expected output:
```text
============================= 26 passed in 10-15s =============================
```

---

## 14. Known Limitations & Future Enhancements

### Limitations
- **Administrator Elevation**: Basic monitoring operates without elevated privileges; detailed information on protected system services (e.g. system idle processes) is guarded by Windows NT security descriptors.
- **Hardware Temperature Sensors**: CPU thermal zones require third-party kernel drivers (e.g. OpenHardwareMonitor or CoreTemp) on Windows.

### Future Enhancements
- GPU acceleration monitoring via NVML (`pynvml`) for NVIDIA graphics cards.
- Network connection topology viewer mapping active TCP/UDP socket connections to specific PIDs.
- Automated email/webhook notifications for critical threshold breaches.
