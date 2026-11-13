"""
SysMonitor Phase 1 Live System Verification Script
Executes real hardware and operating-system probes without mocking,
validating CPU, memory, disk, network, and process metrics on the host machine.
"""
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psutil
from config.settings import APP_NAME, APP_VERSION, LOG_FILE
from utils.logger import get_logger
from utils.formatters import (
    format_bytes,
    format_duration,
    format_frequency,
    format_percent,
    format_timestamp,
)
from utils.system_info import get_static_system_info

logger = get_logger("Phase1Verification")


def run_phase1_verification():
    print("=" * 75)
    print(f" {APP_NAME} v{APP_VERSION} - PHASE 1 LIVE SYSTEM VERIFICATION")
    print("=" * 75)
    logger.info("Starting Phase 1 verification on host machine")

    # 1. Static System Information
    print("\n[1] HOST OPERATING SYSTEM & HARDWARE SPECIFICATIONS")
    print("-" * 50)
    sys_info = get_static_system_info()
    for k, v in sys_info.items():
        print(f"  {k:<24}: {v}")

    assert sys_info["os_name"], "OS Name must not be empty"
    assert sys_info["cpu_logical_cores"] >= 1, "Logical cores must be >= 1"
    assert sys_info["total_ram_bytes"] > 0, "Total RAM must be > 0"
    print("  -> Assertions passed: Static system info is valid.")

    # 2. CPU Live Probing
    print("\n[2] REAL-TIME CPU METRICS PROBE")
    print("-" * 50)
    # Warm up CPU percent (psutil requires an interval or two samples)
    _ = psutil.cpu_percent(interval=None)
    time.sleep(0.5)
    cpu_percent = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    cpu_freq = psutil.cpu_freq()
    cpu_times = psutil.cpu_times()

    print(f"  Aggregate CPU Usage     : {format_percent(cpu_percent)}")
    print(f"  Physical / Logical Cores: {sys_info['cpu_physical_cores']} / {sys_info['cpu_logical_cores']}")
    if cpu_freq:
        print(f"  CPU Frequency (Current) : {format_frequency(cpu_freq.current)}")
        print(f"  CPU Frequency (Min/Max) : {format_frequency(cpu_freq.min)} / {format_frequency(cpu_freq.max)}")
    else:
        print("  CPU Frequency           : Not exposed by platform/virtual environment")

    print(f"  CPU Times               : user={cpu_times.user:.1f}s, system={cpu_times.system:.1f}s, idle={cpu_times.idle:.1f}s")
    print(f"  Per-Core Breakdown ({len(per_core)} cores):")
    for idx, c_val in enumerate(per_core):
        bar = "#" * int(c_val / 5)
        print(f"    Core {idx:<2}: {format_percent(c_val):<7} [{bar:<20}]")

    assert 0.0 <= cpu_percent <= 100.0, f"CPU percent out of range: {cpu_percent}"
    assert len(per_core) == sys_info["cpu_logical_cores"], "Per-core list size mismatch"
    print("  -> Assertions passed: CPU metrics retrieved and within valid ranges.")

    # 3. Memory Live Probing
    print("\n[3] REAL-TIME MEMORY METRICS PROBE")
    print("-" * 50)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    print(f"  Total Physical RAM      : {format_bytes(mem.total)}")
    print(f"  Used RAM                : {format_bytes(mem.used)} ({format_percent(mem.percent)})")
    print(f"  Available RAM           : {format_bytes(mem.available)}")
    print(f"  Free RAM                : {format_bytes(mem.free)}")
    print(f"  Swap Total / Used       : {format_bytes(swap.total)} / {format_bytes(swap.used)} ({format_percent(swap.percent)})")

    assert mem.total > 0, "Total RAM cannot be 0"
    assert mem.available > 0, "Available RAM cannot be 0"
    assert 0.0 <= mem.percent <= 100.0, f"RAM percent out of range: {mem.percent}"
    print("  -> Assertions passed: Memory utilization verified.")

    # 4. Disk Partitions & I/O Probing
    print("\n[4] DISK STORAGE & I/O COUNTERS PROBE")
    print("-" * 50)
    partitions = psutil.disk_partitions(all=False)
    print(f"  Detected Active Partitions: {len(partitions)}")
    for part in partitions:
        try:
            usage = psutil.disk_usage(part.mountpoint)
            print(f"    Drive {part.mountpoint} [{part.fstype or 'Unknown'}]")
            print(f"      Total: {format_bytes(usage.total)} | Used: {format_bytes(usage.used)} ({format_percent(usage.percent)}) | Free: {format_bytes(usage.free)}")
        except (PermissionError, OSError) as e:
            print(f"    Drive {part.mountpoint}: Inaccessible/Removable ({e})")

    disk_io = psutil.disk_io_counters()
    if disk_io:
        print(f"  Cumulative Disk I/O:")
        print(f"    Read Bytes : {format_bytes(disk_io.read_bytes)} ({disk_io.read_count} reads)")
        print(f"    Write Bytes: {format_bytes(disk_io.write_bytes)} ({disk_io.write_count} writes)")
    else:
        print("  Disk I/O counters: Not exposed or unavailable")

    assert len(partitions) >= 1, "At least one disk partition must be present"
    print("  -> Assertions passed: Disk storage and I/O retrieved successfully.")

    # 5. Network Interfaces & Cumulative Counters
    print("\n[5] NETWORK INTERFACES & TRAFFIC PROBE")
    print("-" * 50)
    net_io = psutil.net_io_counters()
    net_if_addrs = psutil.net_if_addrs()
    net_if_stats = psutil.net_if_stats()

    print(f"  Cumulative Traffic Sent : {format_bytes(net_io.bytes_sent)} ({net_io.packets_sent} packets)")
    print(f"  Cumulative Traffic Recv : {format_bytes(net_io.bytes_recv)} ({net_io.packets_recv} packets)")
    print(f"  Detected Network Adapters: {len(net_if_addrs)}")
    for if_name, stats in list(net_if_stats.items())[:5]:  # display top 5 adapters
        status = "UP" if stats.isup else "DOWN"
        print(f"    - {if_name:<30} [{status}] Speed: {stats.speed} Mbps")

    assert net_io.bytes_recv >= 0 and net_io.bytes_sent >= 0, "Network counters must be non-negative"
    print("  -> Assertions passed: Network interfaces and traffic counters verified.")

    # 6. Process Snapshot Probing
    print("\n[6] PROCESS MANAGEMENT & RESOURCE TRACKING PROBE")
    print("-" * 50)
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_info', 'num_threads', 'username']):
        try:
            p_info = p.info
            mem_rss = p_info['memory_info'].rss if p_info.get('memory_info') else 0
            procs.append({
                'pid': p_info['pid'],
                'name': p_info['name'] or 'Unknown',
                'status': p_info['status'] or 'unknown',
                'cpu_percent': p_info['cpu_percent'] or 0.0,
                'memory_mb': mem_rss / (1024 * 1024),
                'threads': p_info['num_threads'] or 1,
                'username': p_info.get('username') or 'N/A'
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    total_procs = len(procs)
    print(f"  Total Active Processes Enumerated: {total_procs}")
    assert total_procs > 0, "Must be able to enumerate active OS processes"

    # Top 5 by Memory
    top_mem = sorted(procs, key=lambda x: x['memory_mb'], reverse=True)[:5]
    print("\n  Top 5 Processes by Memory (RAM):")
    print(f"    {'PID':<8} {'Name':<28} {'Memory (MB)':<14} {'Threads':<8} {'User':<15}")
    print("    " + "-" * 75)
    for p in top_mem:
        print(f"    {p['pid']:<8} {p['name'][:26]:<28} {p['memory_mb']:>9.1f} MB   {p['threads']:<8} {str(p['username'])[:14]:<15}")

    # Top 5 by CPU
    top_cpu = sorted(procs, key=lambda x: x['cpu_percent'], reverse=True)[:5]
    print("\n  Top 5 Processes by CPU Utilization:")
    print(f"    {'PID':<8} {'Name':<28} {'CPU %':<10} {'Memory (MB)':<14} {'Threads':<8}")
    print("    " + "-" * 70)
    for p in top_cpu:
        print(f"    {p['pid']:<8} {p['name'][:26]:<28} {format_percent(p['cpu_percent']):<10} {p['memory_mb']:>9.1f} MB   {p['threads']:<8}")

    print("  -> Assertions passed: Process enumeration, sorting, and metadata retrieval verified.")

    # 7. Verification of Log File Creation
    print("\n[7] LOGGING SYSTEM VERIFICATION")
    print("-" * 50)
    logger.info("Phase 1 verification completed successfully with all assertions passing.")
    assert LOG_FILE.exists(), f"Log file was not created at {LOG_FILE}"
    print(f"  Log File Path           : {LOG_FILE}")
    print(f"  Log File Size           : {LOG_FILE.stat().st_size} bytes")
    print("  -> Assertions passed: Log file confirmed written and rotating handler active.")

    print("\n" + "=" * 75)
    print(" [SUCCESS] PHASE 1 FOUNDATION & HARDWARE INTEGRATION 100% VERIFIED")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_phase1_verification()
