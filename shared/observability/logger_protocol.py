from __future__ import annotations

"""Common logging protocol definitions for workspace observability."""

from collections.abc import Mapping
from typing import Literal, Protocol, TypeAlias, runtime_checkable

LogLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
JsonScalar: TypeAlias = str | int | float | bool | None
JsonObject: TypeAlias = dict[str, object]
JsonValue: TypeAlias = JsonScalar | JsonObject | list[object]
LogExtra: TypeAlias = Mapping[str, object]


@runtime_checkable
class LoggerProtocol(Protocol):
    """Workspace-wide structured logging surface."""

    def debug(
        self,
        message: str,
        *args: object,
        extra: LogExtra | None = None,
        **kwargs: object,
    ) -> None:
        ...

    def info(
        self,
        message: str,
        *args: object,
        extra: LogExtra | None = None,
        **kwargs: object,
    ) -> None:
        ...

    def warning(
        self,
        message: str,
        *args: object,
        extra: LogExtra | None = None,
        **kwargs: object,
    ) -> None:
        ...

    def error(
        self,
        message: str,
        *args: object,
        extra: LogExtra | None = None,
        **kwargs: object,
    ) -> None:
        ...

    def critical(
        self,
        message: str,
        *args: object,
        extra: LogExtra | None = None,
        **kwargs: object,
    ) -> None:
        ...

    def event(
        self,
        level: LogLevel,
        message: str,
        *,
        extra: LogExtra | None = None,
        **kwargs: object,
    ) -> None:
        ...

    def performance(
        self,
        operation: str,
        duration_ms: float,
        *,
        level: LogLevel = "INFO",
        status: str = "ok",
        extra: LogExtra | None = None,
        **kwargs: object,
    ) -> None:
        ...
