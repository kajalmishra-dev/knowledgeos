import json
import logging
import logging.config
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings


class StructuredFormatter(logging.Formatter):
    """Emit single-line JSON log records for structured logging pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def build_logging_config(settings: Settings) -> dict[str, Any]:
    log_level = settings.log_level.upper()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "structured",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"level": log_level, "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": log_level, "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": log_level, "handlers": ["console"], "propagate": False},
        },
    }


def setup_logging(settings: Settings) -> None:
    logging.config.dictConfig(build_logging_config(settings))
    logging.getLogger(__name__).info(
        "Logging configured",
        extra={
            "service": settings.app_name,
            "environment": settings.environment,
        },
    )
