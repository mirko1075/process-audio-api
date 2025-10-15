"""Central logging configuration for the Flask app."""
from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    """Configure root logging handlers.

    The configuration favours JSON-style logs in production (when the
    ``LOG_FORMAT`` environment variable equals ``json``) to integrate nicely with
    cloud logging platforms.  Otherwise a human readable format is used for
    local development.
    """

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text")

    if log_format == "json":
        formatter = logging.Formatter(
            "{\"timestamp\": "
            "%(asctime)s, \"level\": \"%(levelname)s\", "
            "\"name\": \"%(name)s\", \"message\": \"%(message)s\"}"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
        )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
