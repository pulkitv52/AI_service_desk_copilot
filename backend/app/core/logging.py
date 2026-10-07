import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger with standard formatting."""
    numeric_level: int = getattr(logging, log_level.upper(), logging.INFO)

    log_format = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Retrieve logger instance with given name."""
    return logging.getLogger(name or "service_desk")
