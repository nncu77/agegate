"""Structured logging configuration.

Uses JSON-formatted output in production for log aggregation,
human-readable format in development.
"""
import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure root logger based on environment."""
    level = logging.INFO if settings.api_env == "production" else logging.DEBUG

    if settings.api_env == "production":
        # JSON logs for production (e.g. Railway log drain → Datadog/Logtail)
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("insightface").setLevel(logging.WARNING)
