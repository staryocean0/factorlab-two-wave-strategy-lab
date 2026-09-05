from __future__ import annotations

"""Shared ``contextvars`` helpers for canonical log propagation."""

from collections.abc import Callable, Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
import os
import re
import secrets
from typing import Final, Literal

ContextPropagationMode = Literal["off", "compat", "strict"]
CONTEXT_FIELD_NAMES: Final[tuple[str, ...]] = (
    "request_id",
    "trace_id",
    "instance_id",
    "job_id",
    "correlation_id",
    "user_id",
)
CONTEXT_ENVIRONMENT_FIELDS: Final[dict[str, str]] = {
    "request_id": "QUANT_REQUEST_ID",
    "trace_id": "QUANT_TRACE_ID",
    "correlation_id": "QUANT_CORRELATION_ID",
    "job_id": "QUANT_JOB_ID",
    "instance_id": "QUANT_INSTANCE_ID",
    "user_id": "QUANT_USER_ID",
}

_IDENTIFIER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
)
_TRACE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{32}$")
_UNSET: Final[object] = object()

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)
job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)
instance_id_var: ContextVar[str | None] = ContextVar("instance_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)

_CONTEXT_VARS: Final[dict[str, ContextVar[str | None]]] = {
    "request_id": request_id_var,
    "trace_id": trace_id_var,
    "correlation_id": correlation_id_var,
    "job_id": job_id_var,
    "instance_id": instance_id_var,
    "user_id": user_id_var,
}


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    request_id: str | None
    trace_id: str | None
    correlation_id: str | None = None
    job_id: str | None = None
    instance_id: str | None = None
    user_id: str | None = None

    def as_dict(self, *, include_none: bool = False) -> dict[str, str | None]:
        values: dict[str, str | None] = {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "job_id": self.job_id,
            "instance_id": self.instance_id,
            "user_id": self.user_id,
        }
        if include_none:
            return values
        return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True, slots=True)
class ResolvedContext:
    request_id: str
    trace_id: str
    correlation_id: str | None = None
    job_id: str | None = None
    instance_id: str | None = None
    user_id: str | None = None

    def as_dict(self, *, include_none: bool = False) -> dict[str, str | None]:
        values: dict[str, str | None] = {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "job_id": self.job_id,
            "instance_id": self.instance_id,
            "user_id": self.user_id,
        }
        if include_none:
            return values
        return {key: value for key, value in values.items() if value is not None}


def generate_request_id() -> str:
    """Generate a canonical request id matching the v1 schema."""

    return f"req_{secrets.token_hex(6)}"


def generate_trace_id() -> str:
    """Generate a canonical 32-hex trace id."""

    return secrets.token_hex(16)


def normalize_context_value(field_name: str, value: object) -> str | None:
    """Normalize a single context field to the schema-compatible wire form."""

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if field_name == "trace_id":
        lowered = text.lower()
        return lowered if _TRACE_ID_PATTERN.fullmatch(lowered) else None

    if field_name == "user_id":
        return text if len(text) <= 256 else None

    if field_name in {"request_id", "instance_id", "job_id", "correlation_id"}:
        return text if _IDENTIFIER_PATTERN.fullmatch(text) else None

    raise ValueError(f"Unsupported context field: {field_name}")


def snapshot_context() -> ContextSnapshot:
    """Read the current contextvars snapshot."""

    return ContextSnapshot(
        request_id=request_id_var.get(),
        trace_id=trace_id_var.get(),
        correlation_id=correlation_id_var.get(),
        job_id=job_id_var.get(),
        instance_id=instance_id_var.get(),
        user_id=user_id_var.get(),
    )


def resolve_context(
    *,
    request_id: object = _UNSET,
    trace_id: object = _UNSET,
    correlation_id: object = _UNSET,
    job_id: object = _UNSET,
    instance_id: object = _UNSET,
    user_id: object = _UNSET,
    mode: ContextPropagationMode = "compat",
    bind: bool = False,
) -> ResolvedContext:
    """Resolve the current log context with optional generation or strict checks."""

    current = snapshot_context()

    request_id_value = _resolve_required_field(
        "request_id",
        current.request_id if request_id is _UNSET else request_id,
        mode,
        generate_request_id,
    )
    trace_id_value = _resolve_required_field(
        "trace_id",
        current.trace_id if trace_id is _UNSET else trace_id,
        mode,
        generate_trace_id,
    )
    resolved = ResolvedContext(
        request_id=request_id_value,
        trace_id=trace_id_value,
        correlation_id=_resolve_optional_field(
            "correlation_id",
            current.correlation_id if correlation_id is _UNSET else correlation_id,
        ),
        job_id=_resolve_optional_field(
            "job_id",
            current.job_id if job_id is _UNSET else job_id,
        ),
        instance_id=_resolve_optional_field(
            "instance_id",
            current.instance_id if instance_id is _UNSET else instance_id,
        ),
        user_id=_resolve_optional_field(
            "user_id",
            current.user_id if user_id is _UNSET else user_id,
        ),
    )
    if bind:
        _ = _bind_resolved_context(resolved)
    return resolved


def bind_context(
    *,
    request_id: object = _UNSET,
    trace_id: object = _UNSET,
    correlation_id: object = _UNSET,
    job_id: object = _UNSET,
    instance_id: object = _UNSET,
    user_id: object = _UNSET,
    mode: ContextPropagationMode = "compat",
) -> dict[str, Token[str | None]]:
    """Bind a canonical context snapshot into current contextvars."""

    resolved = resolve_context(
        request_id=request_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
        job_id=job_id,
        instance_id=instance_id,
        user_id=user_id,
        mode=mode,
        bind=False,
    )
    return _bind_resolved_context(resolved)


def bind_context_from_environment(
    environment: Mapping[str, str] | None = None,
    *,
    mode: ContextPropagationMode = "compat",
) -> ResolvedContext:
    """Import context from environment variables and bind it."""

    source = os.environ if environment is None else environment
    return resolve_context(
        request_id=source.get(CONTEXT_ENVIRONMENT_FIELDS["request_id"]),
        trace_id=source.get(CONTEXT_ENVIRONMENT_FIELDS["trace_id"]),
        correlation_id=source.get(CONTEXT_ENVIRONMENT_FIELDS["correlation_id"]),
        job_id=source.get(CONTEXT_ENVIRONMENT_FIELDS["job_id"]),
        instance_id=source.get(CONTEXT_ENVIRONMENT_FIELDS["instance_id"]),
        user_id=source.get(CONTEXT_ENVIRONMENT_FIELDS["user_id"]),
        mode=mode,
        bind=True,
    )


def export_context_to_environment(
    environment: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    """Export the currently bound context into environment-style keys."""

    exported = {} if environment is None else dict(environment)
    for field_name, value in snapshot_context().as_dict().items():
        if value is not None:
            exported[CONTEXT_ENVIRONMENT_FIELDS[field_name]] = value
    return exported


def clear_context() -> dict[str, Token[str | None]]:
    """Clear all managed context variables."""

    tokens: dict[str, Token[str | None]] = {}
    for field_name, context_var in _CONTEXT_VARS.items():
        tokens[field_name] = context_var.set(None)
    return tokens


def reset_context(tokens: Mapping[str, Token[str | None]]) -> None:
    """Reset a previously bound context snapshot."""

    for field_name, token in tokens.items():
        context_var = _CONTEXT_VARS.get(field_name)
        if context_var is not None:
            context_var.reset(token)


@contextmanager
def bound_context(
    *,
    request_id: object = _UNSET,
    trace_id: object = _UNSET,
    correlation_id: object = _UNSET,
    job_id: object = _UNSET,
    instance_id: object = _UNSET,
    user_id: object = _UNSET,
    mode: ContextPropagationMode = "compat",
) -> Iterator[ResolvedContext]:
    """Context manager that binds and automatically resets log context."""

    resolved = resolve_context(
        request_id=request_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
        job_id=job_id,
        instance_id=instance_id,
        user_id=user_id,
        mode=mode,
        bind=False,
    )
    tokens = _bind_resolved_context(resolved)
    try:
        yield resolved
    finally:
        reset_context(tokens)


def _resolve_required_field(
    field_name: str,
    raw_value: object,
    mode: ContextPropagationMode,
    generator: Callable[[], str],
) -> str:
    normalized = normalize_context_value(field_name, raw_value)
    if normalized is not None:
        return normalized
    if mode == "strict":
        raise ValueError(f"Missing required context field: {field_name}")
    generated = generator()
    generated_value = normalize_context_value(field_name, generated)
    if generated_value is None:
        raise ValueError(f"Failed to generate a valid {field_name}")
    return generated_value


def _resolve_optional_field(field_name: str, raw_value: object) -> str | None:
    if raw_value is _UNSET:
        return None
    return normalize_context_value(field_name, raw_value)


def _bind_resolved_context(resolved: ResolvedContext) -> dict[str, Token[str | None]]:
    tokens: dict[str, Token[str | None]] = {}
    for field_name, value in resolved.as_dict(include_none=True).items():
        context_var = _CONTEXT_VARS[field_name]
        tokens[field_name] = context_var.set(value)
    return tokens
