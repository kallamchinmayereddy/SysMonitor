"""
SysMonitor Centralized Logging Utility
Provides rotating file and console logging for all application components.
"""
import logging
from logging.handlers import RotatingFileHandler
import sys
from config.settings import LOG_FILE

_initialized = False


def setup_logger(log_level: int = logging.INFO) -> logging.Logger:
    """Configures the root SysMonitor logger with file and console handlers."""
    global _initialized
    logger = logging.getLogger("SysMonitor")

    if _initialized:
        return logger

    logger.setLevel(log_level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating File Handler (5 MB max, 3 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning("Could not initialize file logger: %s", e)

    _initialized = True
    return logger


def get_logger(module_name: str = "") -> logging.Logger:
    """Returns a logger instance prefixed with SysMonitor."""
    setup_logger()
    if module_name:
        return logging.getLogger(f"SysMonitor.{module_name}")
    return logging.getLogger("SysMonitor")
