"""
Basic application logging configuration.

Keeps logging setup in one place so every module can just do:
    import logging
    logger = logging.getLogger(__name__)
"""

import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure root logging handlers and format. Call once at startup."""
    settings = get_settings()

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if configure_logging() is called more than once
    # (e.g. under a reloader).
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Quiet down noisy third-party loggers a little in normal operation.
    logging.getLogger("uvicorn.access").setLevel(log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
