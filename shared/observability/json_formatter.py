from __future__ import annotations

"""Canonical JSON formatter for workspace log events."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import json
import logging
import math
from pathlib import PurePath
import traceback
from typing import Final

from .context import CONTEXT_FIELD_NAMES, ContextPropagationMode, resolve_context

_STANDARD_RECORD_FIELDS: Final[frozenset[str]] = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | frozenset({"message", "asctime"})
_TOP_LEVEL_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "message",
        *CONTEXT_FIELD_NAMES,
        "extra",
    }
)
_LEVEL_NAMES: Final[dict[int, str]] = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class JsonFormatter(logging.Formatter):
    """Render stdlib log records to the canonical v1 JSON schema."""

    _context_mode: ContextPropagationMode

    def __init__(self, *, context_mode: ContextPropagationMode = "compat") -> None:
        super().__init__()
        self._context_mode = context_mode

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            self.format_to_event(record),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )

    def format_to_event(self, record: logging.LogRecord) -> dict[str, object]:
        event_extra = self._extract_event_extra(record)
        context_overrides = {
            field_name: event_extra.pop(field_name)
            for field_name in CONTEXT_FIELD_NAMES
            if field_name in event_extra
        }

        mode: ContextPropagationMode = (
            "compat" if self._context_mode == "off" else self._context_mode
        )
        context_values: dict[str, object] = {}
        for field_name in CONTEXT_FIELD_NAMES:
            if hasattr(record, field_name):
                context_values[field_name] = getattr(record, field_name)
            elif field_name in context_overrides:
                context_values[field_name] = context_overrides[field_name]
        resolved_context = resolve_context(
            mode=mode,
            bind=self._context_mode != "off",
            **context_values,
        )

        if record.exc_info and "exception" not in event_extra:
            event_extra["exception"] = self._format_exception(record.exc_info)
        if record.stack_info and "stack_info" not in event_extra:
            event_extra["stack_info"] = record.stack_info

        event: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": self._normalize_level(record),
            "logger": self._normalize_logger_name(record.name),
            "message": self._normalize_message(record.getMessage()),
            "request_id": resolved_context.request_id,
            "trace_id": resolved_context.trace_id,
        }
        for field_name, value in resolved_context.as_dict().items():
            if field_name in {"request_id", "trace_id"}:
                continue
            if value is not None:
                event[field_name] = value
        if event_extra:
            event["extra"] = event_extra
        return event

    def _extract_event_extra(self, record: logging.LogRecord) -> dict[str, object]:
        collected: dict[str, object] = {}
        raw_extra = getattr(record, "extra", None)
        if isinstance(raw_extra, Mapping):
            for key, value in raw_extra.items():
                if key not in _TOP_LEVEL_FIELDS:
                    collected[str(key)] = self._coerce_json_value(value)
        elif raw_extra is not None:
            collected["payload"] = self._coerce_json_value(raw_extra)

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key in _TOP_LEVEL_FIELDS or key == "extra":
                continue
            collected[str(key)] = self._coerce_json_value(value)
        return {
            key: self._coerce_json_value(value)
            for key, value in collected.items()
            if key not in _TOP_LEVEL_FIELDS
        }

    def _normalize_level(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.CRITICAL:
            return "CRITICAL"
        if record.levelno >= logging.ERROR:
            return "ERROR"
        if record.levelno >= logging.WARNING:
            return "WARNING"
        if record.levelno >= logging.INFO:
            return "INFO"
        return "DEBUG"

    def _normalize_logger_name(self, name: str) -> str:
        cleaned = str(name).strip()
        if not cleaned:
            return "observability"
        return cleaned[:128]

    def _normalize_message(self, message: object) -> str:
        cleaned = str(message).strip()
        return cleaned if cleaned else "log event"

    def _format_exception(self, exc_info: object) -> dict[str, object]:
        if not isinstance(exc_info, tuple) or len(exc_info) != 3:
            return {"message": "unavailable"}
        exc_type, exc_value, exc_traceback = exc_info
        formatted_traceback = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        ).strip()
        return {
            "type": getattr(exc_type, "__name__", str(exc_type)),
            "message": str(exc_value),
            "stacktrace": formatted_traceback,
        }

    def _coerce_json_value(self, value: object) -> object:
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else str(value)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.isoformat(timespec="milliseconds")
            return value.astimezone(UTC).isoformat(timespec="milliseconds").replace(
                "+00:00",
                "Z",
            )
        if isinstance(value, PurePath):
            return str(value)
        if isinstance(value, BaseException):
            return {
                "type": value.__class__.__name__,
                "message": str(value),
            }
        if isinstance(value, Mapping):
            return {
                str(key): self._coerce_json_value(item)
                for key, item in value.items()
                if str(key) not in _TOP_LEVEL_FIELDS
            }
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [self._coerce_json_value(item) for item in value]
        if isinstance(value, set):
            return [self._coerce_json_value(item) for item in sorted(value, key=str)]
        return str(value)
