import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variables for correlation and tracing
_ctx_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_ctx_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)
_ctx_parent_span_id: ContextVar[str | None] = ContextVar("parent_span_id", default=None)
_ctx_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)
_ctx_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_ctx_mask: ContextVar[bool] = ContextVar("mask", default=False)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Inject context vars into the record so formatters can include them
        record.trace_id = _ctx_trace_id.get()
        record.span_id = _ctx_span_id.get()
        record.parent_span_id = _ctx_parent_span_id.get()
        record.run_id = _ctx_run_id.get()
        record.request_id = _ctx_request_id.get()
        record.component = getattr(record, "component", None)
        record.operation = getattr(record, "operation", None)
        # Provide default event field if not present
        if not hasattr(record, "event"):
            record.event = record.name
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }

        # Common fields
        for key in (
            "event",
            "trace_id",
            "span_id",
            "parent_span_id",
            "run_id",
            "request_id",
            "component",
            "operation",
            "duration_ms",
            "status",
            "error_type",
            "error_msg",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        # Include any custom extras set on the record (exclude built-ins)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }
            and k not in payload
        }
        if extras:
            payload.update(extras)

        return json.dumps(payload, ensure_ascii=False)


def _coerce_level(level: str | int | None) -> int:
    if isinstance(level, int):
        return level
    if not level:
        return logging.INFO
    try:
        return getattr(logging, str(level).upper())
    except AttributeError:
        return logging.INFO


def init_logging(
    level: str | int | None = None,
    fmt: str | None = None,
    file_path: str | None = None,
    mask: bool | None = None,
    session_id: str | None = None,
    use_stderr: bool | None = None,
) -> logging.Logger:
    """Initialize application-wide logging.

    - level: log level or env `SPECSCRIBE_LOG_LEVEL` (default INFO)
    - fmt: 'json' or 'text' or env `SPECSCRIBE_LOG_FORMAT` (default 'json')
    - file_path: file path or env `SPECSCRIBE_LOG_FILE` (default session-based file)
    - mask: whether to mask sensitive text or env `SPECSCRIBE_LOG_MASK` (default False)
    - session_id: session ID for generating unique log filenames
    - use_stderr: log to stderr instead of stdout for better UX separation (default True)
                 Can be overridden by env `SPECSCRIBE_LOG_STDERR` (1/true/yes/on for True)
    """

    env_level = os.getenv("SPECSCRIBE_LOG_LEVEL")
    env_format = os.getenv("SPECSCRIBE_LOG_FORMAT")
    env_file = os.getenv("SPECSCRIBE_LOG_FILE")
    env_mask = os.getenv("SPECSCRIBE_LOG_MASK")
    env_stderr = os.getenv("SPECSCRIBE_LOG_STDERR")

    resolved_level = _coerce_level(level or env_level or logging.INFO)
    resolved_format = (fmt or env_format or "json").lower()

    # Generate session-based filename only if session_id is provided
    if not (file_path or env_file):
        if session_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            resolved_file = f"conversation_{session_id}_{timestamp}.json"
        else:
            resolved_file = None  # No session_id means use stream output
    else:
        resolved_file = file_path or env_file

    resolved_mask = bool(mask if mask is not None else (env_mask or "").lower() in {"1", "true", "yes", "on"})

    # Default behavior: stdout for backward compatibility
    # Can be overridden to stderr for better UX separation via use_stderr parameter or env var
    resolved_stderr = False  # Default to stdout for backward compatibility
    if use_stderr is not None:
        resolved_stderr = use_stderr
    elif env_stderr is not None:
        resolved_stderr = (env_stderr or "").lower() in {"1", "true", "yes", "on"}

    root = logging.getLogger()
    root.setLevel(resolved_level)

    # Remove existing handlers to avoid duplication on repeated init
    for h in list(root.handlers):
        root.removeHandler(h)

    handler: logging.Handler
    if resolved_file:
        try:
            handler = logging.FileHandler(resolved_file)
        except (OSError, PermissionError) as e:
            # Fall back to stderr if file creation fails (safer than stdout for errors)
            print(
                f"Warning: Could not create log file '{resolved_file}': {e}",
                file=sys.stderr,
            )
            print("Falling back to stderr logging.", file=sys.stderr)
            handler = logging.StreamHandler(sys.stderr)
            resolved_file = None  # Update resolved_file to reflect actual output
    else:
        # Use stderr or stdout based on configuration
        stream = sys.stderr if resolved_stderr else sys.stdout
        handler = logging.StreamHandler(stream)

    formatter: logging.Formatter
    if resolved_format == "json":
        formatter = JsonFormatter()
    else:
        # Simple human-readable format
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(event)s %(message)s [trace=%(trace_id)s span=%(span_id)s]",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())
    root.addHandler(handler)

    # Generate a run_id if not present
    if not _ctx_run_id.get():
        set_run_id(short_uuid())

    set_masking(resolved_mask)

    logger = logging.getLogger("requirements_bot")
    logger.debug(
        "logging initialized",
        extra={
            "event": "logging.init",
            "component": "logging",
            "operation": "init",
            "level": resolved_level,
            "format": resolved_format,
            "file": resolved_file or "stderr",
            "mask": resolved_mask,
        },
    )
    return logger


def short_uuid() -> str:
    return uuid.uuid4().hex[:12]


def set_trace_id(trace_id: str | None) -> None:
    _ctx_trace_id.set(trace_id)


def get_trace_id() -> str | None:
    return _ctx_trace_id.get()


def set_run_id(run_id: str) -> None:
    _ctx_run_id.set(run_id)


def get_run_id() -> str | None:
    return _ctx_run_id.get()


def set_request_id(request_id: str | None) -> None:
    _ctx_request_id.set(request_id)


def get_request_id() -> str | None:
    return _ctx_request_id.get()


def set_masking(mask: bool) -> None:
    _ctx_mask.set(mask)


def is_masking() -> bool:
    return _ctx_mask.get()


def mask_text(text: str) -> str:
    if not is_masking():
        return text
    return f"[masked len={len(text)}]"


@contextmanager
def span(event: str, **fields: Any) -> Iterator[None]:
    """Context manager to time an operation and emit a structured log with correlation fields.

    Usage:
        with span("llm.generate_questions", component="provider", operation="generate_questions", provider="openai"):
            ...
    """

    logger = logging.getLogger("requirements_bot")
    parent = _ctx_span_id.get()
    _ctx_parent_span_id.set(parent)
    current = short_uuid()
    _ctx_span_id.set(current)
    start = time.perf_counter()
    error_type: str | None = None
    error_msg: str | None = None
    try:
        yield
        status = "ok"
    except Exception as e:  # noqa: BLE001 : intentional to capture and re-raise
        status = "error"
        error_type = type(e).__name__
        error_msg = str(e)
        raise
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000.0, 3)
        log_payload: dict[str, Any] = {
            "event": event,
            "component": fields.pop("component", None),
            "operation": fields.pop("operation", None),
            "duration_ms": duration_ms,
            "status": status,
        }
        if error_type:
            log_payload["error_type"] = error_type
            log_payload["error_msg"] = error_msg
        # Merge remaining fields
        log_payload.update(fields)
        logger.info("span", extra=log_payload)
        # restore previous span
        _ctx_span_id.set(parent)
        _ctx_parent_span_id.set(None)


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    logger = logging.getLogger("requirements_bot")
    extra = {"event": event}
    extra.update(fields)
    logger.log(level, event, extra=extra)


def audit_log(event_type: str, user_id: str | None, client_ip: str | None = None, **details: Any) -> None:
    """Log security-relevant events to audit trail.

    Audit logs are always logged at WARNING level to ensure they're captured
    and can be easily filtered for security analysis and compliance reporting.

    Args:
        event_type: Type of security event (e.g., "auth.failed_login", "token.refresh_failed")
        user_id: ID of the user involved (None for anonymous events)
        client_ip: IP address of the client
        **details: Additional context about the security event
    """
    logger = logging.getLogger("requirements_bot")
    extra = {
        "event": f"audit.{event_type}",
        "audit": True,  # Flag for easy audit log filtering
        "user_id": user_id,
        "client_ip": client_ip,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    extra.update(details)
    logger.warning(f"AUDIT: {event_type}", extra=extra)
