from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        for k in ("experiment_id", "trial_id", "strategy", "reward"):
            if hasattr(record, k):
                base[k] = getattr(record, k)

        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    # Replace existing handlers (avoid double logs in uvicorn reload / tests)
    root.handlers = [handler]

    # Quiet some noisy libs a bit
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)