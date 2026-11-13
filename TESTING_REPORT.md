# SysMonitor Testing and Quality Report

## 1. Why the tests take longer than usual

This project does not use mocked metrics. It performs real live probes against the host machine using `psutil`, `SQLite`, background threads, and Streamlit. That makes testing slower than a typical unit-only suite because the tests include:

- real CPU usage sampling and warm-up delays
- real memory and disk metrics collection
- real network traffic counters
- live process enumeration
- SQLite WAL database writes and historical persistence checks
- background monitoring-engine lifecycle tests with thread start/stop checks
- a live Phase 1 verification script that validates actual host hardware and OS telemetry

In short, the suite is testing real system behavior, not synthetic values. That is appropriate for this project and is the reason the runtime is longer than a mocked test suite.

## 2. Test execution summary

The following checks were completed successfully:

- `python -m pytest -q` → 26 passed in 18.20s
- `python verify_phase1.py` → Phase 1 live host verification completed successfully
- Streamlit app launched successfully and the dashboard rendered at `http://localhost:8501/`

## 3. Test coverage areas validated

### Functional tests
- CPU collector behavior
- memory collector behavior
- disk collector behavior
- network collector behavior
- process collector behavior
- monitoring engine lifecycle and singleton behavior
- database schema initialization and persistence
- alert lifecycle and acknowledgment logic
- data pruning and CSV export
- analytics calculations and anomaly detection
- health score logic

### Live verification checks
- OS name and hardware info
- logical and physical core counts
- total RAM and swap size
- uptime and boot time
- live CPU usage and calculations
- per-core utilization
- disk partitions and disk I/O counters
- network adapter detection and cumulative traffic counters
- process enumeration and top consumers
- log file creation and rotating logger behavior

## 4. Result verdict

Overall verdict: PASS

The project is functioning correctly for its intended academic/system-monitoring scope. It is complete, reliable, and demo-ready for a college project and viva.

## 5. Quality assessment

### Strengths
- Real OS telemetry rather than simulated data
- Good modular architecture
- SQLite persistence with pruning and export support
- Clear analytics and anomaly detection logic
- Good alert management and cooldown handling
- Strong test coverage for core functionality

### Minor limitations
- Some UI states could be more explicit for first-time users
- Several outputs are technically correct but not fully polished for production UX
- Performance benchmarking under long-duration heavy use was not formally measured

## 6. Final conclusion

The longer test time is a direct result of live, real-environment verification. The project passed its test suite and live verification successfully, and it is in a strong state for demonstration.
