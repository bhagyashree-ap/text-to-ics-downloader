"""Structured logging with request-id correlation (spec section 5).

Logs include request_id, service, operation, duration_ms, outcome. Never logs raw
email/document content, API keys, or other sensitive data.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:16]
    _request_id.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    _request_id.set(rid or "-")


def get_request_id() -> str:
    return _request_id.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "request_id": get_request_id(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("service", "operation", "duration_ms", "outcome"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


log = logging.getLogger("chronos")


@contextmanager
def operation(service: str, op: str):
    """Log the start/outcome/duration of a service operation."""
    start = time.monotonic()
    outcome = "ok"
    try:
        yield
    except Exception:
        outcome = "error"
        raise
    finally:
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        log.info(
            "%s.%s %s",
            service,
            op,
            outcome,
            extra={"service": service, "operation": op, "duration_ms": duration_ms, "outcome": outcome},
        )
