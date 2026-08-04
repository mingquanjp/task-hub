"""Structured logging configuration for TaskHub."""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from taskhub.core.config import get_settings


def configure_logging() -> None:
    """Configure structured JSON logging."""
    settings = get_settings()

    # Create a custom json logger formatter
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "levelname": "level",
            "asctime": "timestamp",
            "name": "logger",
        },
    )

    # Use a stream handler printing to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Set root logger
    root_logger = logging.getLogger()
    # Remove existing handlers
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)

    level_name = settings.log_level.upper()
    try:
        level = getattr(logging, level_name)
    except AttributeError:
        level = logging.INFO

    root_logger.setLevel(level)

    # Uvicorn loggers should also use our formatter
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.propagate = False
