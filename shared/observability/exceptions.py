"""Canonical workspace exception foundation."""

from __future__ import annotations

from typing import NoReturn, TypeAlias
from uuid import uuid4

from .error_codes import ErrorCodeDefinition, get_error_definition, resolve_canonical_code

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def _new_request_id() -> str:
    return f"req_{uuid4().hex[:12]}"


def _new_trace_id() -> str:
    return uuid4().hex


class QuantException(Exception):
    """Workspace-wide canonical exception with legacy compatibility fields."""

    def __init__(
        self,
        message: str,
        *,
        canonical_code: str | None = None,
        error_code: str | None = None,
        code: str | None = None,
        legacy_code: str | None = None,
        category: str | None = None,
        http_status: int | None = None,
        status_code: int | None = None,
        retryable: bool | None = None,
        details: dict[str, JsonValue] | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        meta: dict[str, JsonValue] | None = None,
        job_id: str | None = None,
        instance_id: str | None = None,
        correlation_id: str | None = None,
        recovery_hint: str | None = None,
    ) -> None:
        resolved_status = status_code if status_code is not None else http_status
        resolved_code = resolve_canonical_code(
            canonical_code=canonical_code,
            error_code=error_code,
            code=code,
            legacy_code=legacy_code,
            status_code=resolved_status,
            message=message,
        )
        definition = get_error_definition(resolved_code)
        self.message = message
        self.canonical_code = definition.canonical_code
        self.category = category or definition.category
        self.http_status = resolved_status or definition.http_status
        self.retryable = definition.retryable if retryable is None else retryable
        self.error_code = error_code or definition.error_code
        self.code = code or definition.code
        self.legacy_code = legacy_code or definition.legacy_code
        self.details = dict(details or {})
        self.request_id = str(request_id or _new_request_id())
        self.trace_id = self._normalize_trace_id(trace_id)
        self.meta = dict(meta or {})
        self.job_id = job_id
        self.instance_id = instance_id
        self.correlation_id = correlation_id
        self.recovery_hint = recovery_hint
        super().__init__(message)

    @staticmethod
    def _normalize_trace_id(trace_id: str | None) -> str:
        candidate = str(trace_id or "").strip().lower()
        if len(candidate) == 32 and all(ch in "0123456789abcdef" for ch in candidate):
            return candidate
        return _new_trace_id()

    @property
    def status_code(self) -> int:
        return self.http_status

    @property
    def definition(self) -> ErrorCodeDefinition:
        return get_error_definition(self.canonical_code)

    def bind_context(
        self,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
        meta: dict[str, JsonValue] | None = None,
    ) -> "QuantException":
        if request_id:
            self.request_id = str(request_id)
        if trace_id:
            self.trace_id = self._normalize_trace_id(trace_id)
        if meta:
            self.meta.update(meta)
        return self

    def to_error_dict(self, *, include_request_id: bool = False) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "canonical_code": self.canonical_code,
            "category": self.category,
            "message": self.message,
            "retryable": self.retryable,
            "http_status": self.http_status,
            "details": dict(self.details),
        }
        if self.error_code:
            payload["error_code"] = self.error_code
        if self.code:
            payload["code"] = self.code
        if self.legacy_code:
            payload["legacy_code"] = self.legacy_code
        if self.job_id:
            payload["job_id"] = self.job_id
        if self.instance_id:
            payload["instance_id"] = self.instance_id
        if self.correlation_id:
            payload["correlation_id"] = self.correlation_id
        if self.recovery_hint:
            payload["recovery_hint"] = self.recovery_hint
        if include_request_id:
            payload["request_id"] = self.request_id
        return payload

    def to_envelope(
        self,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
        meta: dict[str, JsonValue] | None = None,
        include_error_request_id: bool = False,
    ) -> dict[str, JsonValue]:
        self.bind_context(request_id=request_id, trace_id=trace_id, meta=meta)
        payload: dict[str, JsonValue] = {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "error": self.to_error_dict(include_request_id=include_error_request_id),
        }
        if self.meta:
            payload["meta"] = dict(self.meta)
        return payload

    def to_dict(self) -> dict[str, JsonValue]:
        return self.to_envelope()

    @classmethod
    def raise_from(cls, cause: BaseException, *args, **kwargs) -> NoReturn:
        raise cls(*args, **kwargs) from cause
