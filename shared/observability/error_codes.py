"""Canonical error registry and compatibility resolvers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorCodeDefinition:
    canonical_code: str
    category: str
    http_status: int
    retryable: bool
    default_message: str
    error_code: str | None = None
    code: str | None = None
    legacy_code: str | None = None


ERROR_CODE_REGISTRY: dict[str, ErrorCodeDefinition] = {
    "QNT.AUTH.AUTHENTICATION_REQUIRED": ErrorCodeDefinition(
        canonical_code="QNT.AUTH.AUTHENTICATION_REQUIRED",
        category="auth",
        http_status=401,
        retryable=False,
        default_message="Authentication is required",
        error_code="authentication_required",
        code="E_UNAUTHORIZED",
    ),
    "QNT.AUTH.PERMISSION_DENIED": ErrorCodeDefinition(
        canonical_code="QNT.AUTH.PERMISSION_DENIED",
        category="auth",
        http_status=403,
        retryable=False,
        default_message="Permission denied",
        error_code="permission_denied",
        code="E_UNAUTHORIZED",
        legacy_code="TRADING_009",
    ),
    "QNT.AUTH.UPSTREAM_AUTH_FAILED": ErrorCodeDefinition(
        canonical_code="QNT.AUTH.UPSTREAM_AUTH_FAILED",
        category="auth",
        http_status=502,
        retryable=False,
        default_message="Upstream authentication failed",
    ),
    "QNT.CLIENT.HEADLESS_REQUEST_FAILED": ErrorCodeDefinition(
        canonical_code="QNT.CLIENT.HEADLESS_REQUEST_FAILED",
        category="client",
        http_status=400,
        retryable=False,
        default_message="Headless client request failed",
        code="E_HEADLESS_CLIENT",
    ),
    "QNT.CONFLICT.ALREADY_CONNECTED": ErrorCodeDefinition(
        canonical_code="QNT.CONFLICT.ALREADY_CONNECTED",
        category="conflict",
        http_status=409,
        retryable=False,
        default_message="Gateway is already connected",
        legacy_code="TRADING_004",
    ),
    "QNT.CONFLICT.CONFIRMATION_REQUIRED": ErrorCodeDefinition(
        canonical_code="QNT.CONFLICT.CONFIRMATION_REQUIRED",
        category="conflict",
        http_status=409,
        retryable=False,
        default_message="Explicit confirmation is required",
        code="E_CONFIRMATION_REQUIRED",
    ),
    "QNT.CONFLICT.RESOURCE_CONFLICT": ErrorCodeDefinition(
        canonical_code="QNT.CONFLICT.RESOURCE_CONFLICT",
        category="conflict",
        http_status=409,
        retryable=False,
        default_message="Resource conflict",
        code="E_CONFLICT",
        legacy_code="TRADING_011",
    ),
    "QNT.EXTERNAL.CONNECT_FAILED": ErrorCodeDefinition(
        canonical_code="QNT.EXTERNAL.CONNECT_FAILED",
        category="external",
        http_status=503,
        retryable=True,
        default_message="External connection failed",
        legacy_code="TRADING_003",
    ),
    "QNT.EXTERNAL.OPERATION_FAILED": ErrorCodeDefinition(
        canonical_code="QNT.EXTERNAL.OPERATION_FAILED",
        category="external",
        http_status=502,
        retryable=True,
        default_message="External operation failed",
        legacy_code="TRADING_007",
    ),
    "QNT.EXTERNAL.PROTOCOL_ERROR": ErrorCodeDefinition(
        canonical_code="QNT.EXTERNAL.PROTOCOL_ERROR",
        category="external",
        http_status=502,
        retryable=False,
        default_message="External protocol error",
    ),
    "QNT.EXTERNAL.TIMEOUT": ErrorCodeDefinition(
        canonical_code="QNT.EXTERNAL.TIMEOUT",
        category="timeout",
        http_status=504,
        retryable=True,
        default_message="External operation timed out",
    ),
    "QNT.LIMIT.GATEWAY_LIMIT_EXCEEDED": ErrorCodeDefinition(
        canonical_code="QNT.LIMIT.GATEWAY_LIMIT_EXCEEDED",
        category="rate_limit",
        http_status=429,
        retryable=True,
        default_message="Gateway limit exceeded",
        legacy_code="TRADING_012",
    ),
    "QNT.LIMIT.RATE_LIMITED": ErrorCodeDefinition(
        canonical_code="QNT.LIMIT.RATE_LIMITED",
        category="rate_limit",
        http_status=429,
        retryable=True,
        default_message="Rate limit exceeded",
        code="E_RATE_LIMITED",
    ),
    "QNT.NOT_FOUND.DATASET": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.DATASET",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Dataset was not found",
        error_code="dataset_not_found",
    ),
    "QNT.NOT_FOUND.GATEWAY": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.GATEWAY",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Gateway was not found",
    ),
    "QNT.NOT_FOUND.INSTRUMENT": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.INSTRUMENT",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Instrument was not found",
        error_code="instrument_not_found",
    ),
    "QNT.NOT_FOUND.JOB": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.JOB",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Job was not found",
        error_code="job_not_found",
    ),
    "QNT.NOT_FOUND.PLAN": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.PLAN",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Plan was not found",
        error_code="plan_not_found",
    ),
    "QNT.NOT_FOUND.PUBLISH_RUN": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.PUBLISH_RUN",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Publish run was not found",
        error_code="publish_run_not_found",
    ),
    "QNT.NOT_FOUND.RESOURCE": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.RESOURCE",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Resource was not found",
        code="E_NOT_FOUND",
        legacy_code="TRADING_006",
    ),
    "QNT.NOT_FOUND.SESSION": ErrorCodeDefinition(
        canonical_code="QNT.NOT_FOUND.SESSION",
        category="not_found",
        http_status=404,
        retryable=False,
        default_message="Session was not found",
        error_code="session_not_found",
    ),
    "QNT.POLICY.GATE_BLOCKED": ErrorCodeDefinition(
        canonical_code="QNT.POLICY.GATE_BLOCKED",
        category="policy",
        http_status=409,
        retryable=False,
        default_message="Governance gate blocked the operation",
        code="E_GATE_BLOCKED",
    ),
    "QNT.POLICY.OPERATION_NOT_ALLOWED": ErrorCodeDefinition(
        canonical_code="QNT.POLICY.OPERATION_NOT_ALLOWED",
        category="policy",
        http_status=403,
        retryable=False,
        default_message="Operation is not allowed",
        error_code="operation_not_allowed",
    ),
    "QNT.RISK.BLOCKED": ErrorCodeDefinition(
        canonical_code="QNT.RISK.BLOCKED",
        category="risk",
        http_status=409,
        retryable=False,
        default_message="Risk control blocked the operation",
        legacy_code="TRADING_008",
    ),
    "QNT.STATE.ALREADY_RUNNING": ErrorCodeDefinition(
        canonical_code="QNT.STATE.ALREADY_RUNNING",
        category="state",
        http_status=409,
        retryable=False,
        default_message="Resource is already running",
    ),
    "QNT.STATE.CANNOT_CANCEL": ErrorCodeDefinition(
        canonical_code="QNT.STATE.CANNOT_CANCEL",
        category="state",
        http_status=409,
        retryable=False,
        default_message="Current state cannot be cancelled",
        error_code="cannot_cancel",
    ),
    "QNT.STATE.JOB_ALREADY_TERMINAL": ErrorCodeDefinition(
        canonical_code="QNT.STATE.JOB_ALREADY_TERMINAL",
        category="state",
        http_status=409,
        retryable=False,
        default_message="Job is already in a terminal state",
        error_code="job_already_terminal",
    ),
    "QNT.STATE.NOT_CONNECTED": ErrorCodeDefinition(
        canonical_code="QNT.STATE.NOT_CONNECTED",
        category="state",
        http_status=409,
        retryable=False,
        default_message="Gateway is not connected",
    ),
    "QNT.SYSTEM.INTERNAL": ErrorCodeDefinition(
        canonical_code="QNT.SYSTEM.INTERNAL",
        category="system",
        http_status=500,
        retryable=True,
        default_message="Internal system error",
        code="E_INTERNAL_ERROR",
        legacy_code="TRADING_010",
    ),
    "QNT.SYSTEM.JOB_ENQUEUE_FAILED": ErrorCodeDefinition(
        canonical_code="QNT.SYSTEM.JOB_ENQUEUE_FAILED",
        category="system",
        http_status=503,
        retryable=True,
        default_message="Job enqueue failed",
        error_code="job_enqueue_failed",
    ),
    "QNT.SYSTEM.NATIVE_FAILURE": ErrorCodeDefinition(
        canonical_code="QNT.SYSTEM.NATIVE_FAILURE",
        category="system",
        http_status=500,
        retryable=False,
        default_message="Native component failure",
    ),
    "QNT.VALIDATION.GATEWAY_TYPE_INVALID": ErrorCodeDefinition(
        canonical_code="QNT.VALIDATION.GATEWAY_TYPE_INVALID",
        category="validation",
        http_status=400,
        retryable=False,
        default_message="Unsupported gateway type",
    ),
    "QNT.VALIDATION.INVALID_CONFIGURATION": ErrorCodeDefinition(
        canonical_code="QNT.VALIDATION.INVALID_CONFIGURATION",
        category="validation",
        http_status=400,
        retryable=False,
        default_message="Invalid configuration",
    ),
    "QNT.VALIDATION.INVALID_REQUEST": ErrorCodeDefinition(
        canonical_code="QNT.VALIDATION.INVALID_REQUEST",
        category="validation",
        http_status=400,
        retryable=False,
        default_message="Invalid request",
        error_code="invalid_request",
        code="E_VALIDATION",
        legacy_code="TRADING_005",
    ),
    "QNT.VALIDATION.INVALID_SYMBOL_SCOPE": ErrorCodeDefinition(
        canonical_code="QNT.VALIDATION.INVALID_SYMBOL_SCOPE",
        category="validation",
        http_status=400,
        retryable=False,
        default_message="Invalid symbol scope",
        error_code="invalid_symbol_scope",
    ),
}


DATAHUB_ERROR_CODE_MAP: dict[str, str] = {
    "authentication_required": "QNT.AUTH.AUTHENTICATION_REQUIRED",
    "permission_denied": "QNT.AUTH.PERMISSION_DENIED",
    "operation_not_allowed": "QNT.POLICY.OPERATION_NOT_ALLOWED",
    "job_not_found": "QNT.NOT_FOUND.JOB",
    "dataset_not_found": "QNT.NOT_FOUND.DATASET",
    "instrument_not_found": "QNT.NOT_FOUND.INSTRUMENT",
    "plan_not_found": "QNT.NOT_FOUND.PLAN",
    "session_not_found": "QNT.NOT_FOUND.SESSION",
    "publish_run_not_found": "QNT.NOT_FOUND.PUBLISH_RUN",
    "job_already_terminal": "QNT.STATE.JOB_ALREADY_TERMINAL",
    "history_stop_not_applicable": "QNT.CONFLICT.RESOURCE_CONFLICT",
    "history_stop_loopback_only": "QNT.POLICY.OPERATION_NOT_ALLOWED",
    "history_stop_unauthorized": "QNT.AUTH.AUTHENTICATION_REQUIRED",
    "history_stop_disabled": "QNT.EXTERNAL.CONNECT_FAILED",
    "use_admin_history_stop": "QNT.POLICY.OPERATION_NOT_ALLOWED",
    "cannot_stop_job": "QNT.STATE.CANNOT_CANCEL",
    "cannot_cancel": "QNT.STATE.CANNOT_CANCEL",
    "job_enqueue_failed": "QNT.SYSTEM.JOB_ENQUEUE_FAILED",
    "invalid_request": "QNT.VALIDATION.INVALID_REQUEST",
    "invalid_symbol_scope": "QNT.VALIDATION.INVALID_SYMBOL_SCOPE",
    "invalid_json": "QNT.VALIDATION.INVALID_REQUEST",
    "missing_job_id": "QNT.VALIDATION.INVALID_REQUEST",
    "invalid_message_type": "QNT.VALIDATION.INVALID_REQUEST",
    "subscription_not_found": "QNT.NOT_FOUND.RESOURCE",
    "native_tdx_core_unavailable": "QNT.SYSTEM.NATIVE_FAILURE",
    "desktop_shutdown_loopback_only": "QNT.POLICY.OPERATION_NOT_ALLOWED",
    "desktop_shutdown_forbidden": "QNT.AUTH.PERMISSION_DENIED",
    "desktop_shutdown_disabled": "QNT.EXTERNAL.CONNECT_FAILED",
    "desktop_shutdown_server_missing": "QNT.EXTERNAL.CONNECT_FAILED",
}

FACTOR_LAB_CODE_MAP: dict[str, str] = {
    "E_VALIDATION": "QNT.VALIDATION.INVALID_REQUEST",
    "E_NOT_FOUND": "QNT.NOT_FOUND.RESOURCE",
    "E_CONFLICT": "QNT.CONFLICT.RESOURCE_CONFLICT",
    "E_CONFIRMATION_REQUIRED": "QNT.CONFLICT.CONFIRMATION_REQUIRED",
    "E_GATE_BLOCKED": "QNT.POLICY.GATE_BLOCKED",
    "E_RATE_LIMITED": "QNT.LIMIT.RATE_LIMITED",
    "E_INTERNAL_ERROR": "QNT.SYSTEM.INTERNAL",
    "E_PUBLISH_VALIDATION": "QNT.VALIDATION.INVALID_REQUEST",
    "E_HEADLESS_CLIENT": "QNT.CLIENT.HEADLESS_REQUEST_FAILED",
}

TDX_SDK_CODE_MAP: dict[str, str] = {
    "TDX_CONN_ERROR": "QNT.EXTERNAL.CONNECT_FAILED",
    "TDX_AUTH_ERROR": "QNT.AUTH.UPSTREAM_AUTH_FAILED",
    "TDX_DATA_ERROR": "QNT.EXTERNAL.OPERATION_FAILED",
    "TDX_PROTOCOL_ERROR": "QNT.EXTERNAL.PROTOCOL_ERROR",
    "TDX_TIMEOUT_ERROR": "QNT.EXTERNAL.TIMEOUT",
    "TDX_CONFIG_ERROR": "QNT.VALIDATION.INVALID_CONFIGURATION",
    "TDX_NATIVE_ERROR": "QNT.SYSTEM.NATIVE_FAILURE",
    "TDX_RETRYABLE_ERROR": "QNT.EXTERNAL.OPERATION_FAILED",
    "TDX_NETWORK_ERROR": "QNT.EXTERNAL.CONNECT_FAILED",
    "TDX_SERVER_ERROR": "QNT.EXTERNAL.OPERATION_FAILED",
    "TDX_HARD_ERROR": "QNT.SYSTEM.INTERNAL",
    "TDX_INVALID_PARAM": "QNT.VALIDATION.INVALID_REQUEST",
    "TDX_UNSUPPORTED_OP": "QNT.POLICY.OPERATION_NOT_ALLOWED",
}

TERMINAL_TRADING_LEGACY_CODES = {
    "TRADING_003",
    "TRADING_004",
    "TRADING_005",
    "TRADING_006",
    "TRADING_007",
    "TRADING_008",
    "TRADING_009",
    "TRADING_010",
    "TRADING_011",
    "TRADING_012",
}


def get_error_definition(canonical_code: str) -> ErrorCodeDefinition:
    return ERROR_CODE_REGISTRY[canonical_code]


def resolve_datahub_error_code(error_code: str) -> str:
    normalized = error_code.strip().lower()
    return DATAHUB_ERROR_CODE_MAP.get(normalized, "QNT.SYSTEM.INTERNAL")


def resolve_factor_lab_code(code: str, *, status_code: int | None = None) -> str:
    normalized = code.strip().upper()
    if normalized == "E_UNAUTHORIZED":
        if status_code == 401:
            return "QNT.AUTH.AUTHENTICATION_REQUIRED"
        if status_code == 403:
            return "QNT.AUTH.PERMISSION_DENIED"
        return "QNT.AUTH.PERMISSION_DENIED"
    return FACTOR_LAB_CODE_MAP.get(normalized, "QNT.SYSTEM.INTERNAL")


def resolve_tdx_sdk_code(code: str) -> str:
    normalized = code.strip().upper()
    return TDX_SDK_CODE_MAP.get(normalized, "QNT.SYSTEM.INTERNAL")


def resolve_terminal_legacy_code(legacy_code: str, *, message: str | None = None) -> str:
    normalized = legacy_code.strip().upper()
    details = (message or "").strip().lower()
    if normalized == "TRADING_003":
        if "unsupported gateway type" in details:
            return "QNT.VALIDATION.GATEWAY_TYPE_INVALID"
        if "gateway not found" in details:
            return "QNT.NOT_FOUND.GATEWAY"
        return "QNT.EXTERNAL.CONNECT_FAILED"
    if normalized == "TRADING_004":
        return "QNT.CONFLICT.ALREADY_CONNECTED"
    if normalized == "TRADING_005":
        return "QNT.VALIDATION.INVALID_REQUEST"
    if normalized == "TRADING_006":
        return "QNT.NOT_FOUND.RESOURCE"
    if normalized == "TRADING_007":
        if "gateway not found" in details:
            return "QNT.NOT_FOUND.GATEWAY"
        if "no gateway connected" in details:
            return "QNT.STATE.NOT_CONNECTED"
        return "QNT.EXTERNAL.OPERATION_FAILED"
    if normalized == "TRADING_008":
        return "QNT.RISK.BLOCKED"
    if normalized == "TRADING_009":
        return "QNT.AUTH.PERMISSION_DENIED"
    if normalized == "TRADING_010":
        if "strategy already running" in details:
            return "QNT.STATE.ALREADY_RUNNING"
        if "no gateway connected" in details:
            return "QNT.STATE.NOT_CONNECTED"
        return "QNT.SYSTEM.INTERNAL"
    if normalized == "TRADING_011":
        return "QNT.CONFLICT.RESOURCE_CONFLICT"
    if normalized == "TRADING_012":
        return "QNT.LIMIT.GATEWAY_LIMIT_EXCEEDED"
    return "QNT.SYSTEM.INTERNAL"


def resolve_canonical_code(
    *,
    canonical_code: str | None = None,
    error_code: str | None = None,
    code: str | None = None,
    legacy_code: str | None = None,
    status_code: int | None = None,
    message: str | None = None,
) -> str:
    if canonical_code is not None:
        normalized = canonical_code.strip().upper()
        if normalized:
            return normalized
    if error_code is not None:
        return resolve_datahub_error_code(error_code)
    if code is not None:
        return resolve_factor_lab_code(code, status_code=status_code)
    if legacy_code is not None:
        return resolve_terminal_legacy_code(legacy_code, message=message)
    raise KeyError("No canonical or compatibility code provided")
