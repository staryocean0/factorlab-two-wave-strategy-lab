# pyright: reportImportCycles=false
"""Shared fail-closed validators for V3 formula-derived contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest

_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "production_authority",
    "dynamic_parameter_authority",
    "tool_routing_authority",
)
_FORBIDDEN_DETAIL_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "trade_pnl_rows", "trade_or_event_rows", "action_rows", "actions",
        "feature_rows", "forward_returns", "event_rows",
    }
)


def require_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"V3 contract requires {key}")
    return value


def require_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValidationError(f"V3 contract requires mapping {key}")
    return cast(Mapping[str, object], value)


def require_sequence(payload: Mapping[str, object], key: str) -> tuple[object, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValidationError(f"V3 contract requires list {key}")
    return tuple(cast(list[object], value))


def require_digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValidationError(f"{field} must be a sha256 digest")
    try:
        _ = int(value[7:], 16)
    except ValueError as exc:
        raise ValidationError(f"{field} must be a sha256 digest") from exc
    return value


def require_zero_authority(payload: Mapping[str, object]) -> None:
    for field in _AUTHORITY_FIELDS:
        if payload.get(field) is not False:
            raise ValidationError(f"V3 contract requires {field}=false")
    _reject_nonzero_authority(payload)


def require_exact_keys(
    payload: Mapping[str, object],
    expected: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    if set(payload) != set(expected):
        raise ValidationError(f"{label} fields changed")


def _reject_nonzero_authority(value: object) -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in cast(Mapping[object, object], value).items():
            key = str(raw_key)
            if key == "field_labels_zh":
                continue
            if (key.endswith("authority") or key == "stage3_authorized") and nested is not False:
                raise ValidationError("V3 contract contains forbidden nested authority")
            if key in _FORBIDDEN_DETAIL_FIELDS:
                raise ValidationError("V3 contract contains forbidden row-level detail")
            _reject_nonzero_authority(nested)
    elif isinstance(value, list):
        for nested in cast(list[object], value):
            _reject_nonzero_authority(nested)


def require_field_labels(payload: Mapping[str, object], required_keys: set[str]) -> None:
    labels = require_mapping(payload, "field_labels_zh")
    missing = required_keys.difference(labels)
    if missing:
        raise ValidationError(f"field_labels_zh missing labels: {sorted(missing)}")
    if any(not isinstance(value, str) or not value.strip() for value in labels.values()):
        raise ValidationError("field_labels_zh values must be non-empty Chinese descriptions")


def attach_semantic_digest(payload: Mapping[str, object]) -> dict[str, object]:
    result = dict(payload)
    if "semantic_digest" in result:
        raise ValidationError("semantic_digest must be attached exactly once")
    result["semantic_digest"] = canonical_digest(result)
    return result


def validate_semantic_digest(payload: Mapping[str, object]) -> None:
    body = dict(payload)
    digest = body.pop("semantic_digest", None)
    _ = require_digest(digest, field="semantic_digest")
    if digest != canonical_digest(body):
        raise ValidationError("V3 contract semantic digest is invalid")


def validate_formula_computation_graph(payload: Mapping[str, object]) -> None:
    """Validate a serialized graph without executing it or reading market data."""

    from factor_lab.market_state.formula_derivation.models import (
        FORMULA_COMPUTATION_GRAPH_SCHEMA_ID,
        FormulaComputationGraph,
    )

    if payload.get("schema_id") != FORMULA_COMPUTATION_GRAPH_SCHEMA_ID:
        raise ValidationError("formula computation graph schema changed")
    require_zero_authority(payload)
    validate_semantic_digest(payload)
    graph = FormulaComputationGraph.from_dict(payload)
    if graph.to_dict() != dict(payload):
        raise ValidationError("formula computation graph does not round-trip canonically")


def validate_formula_derivation_package(payload: Mapping[str, object]) -> None:
    """Validate the zero-data Stage-1 derivation package."""

    from factor_lab.market_state.formula_derivation.models import (
        FORMULA_DERIVATION_PACKAGE_SCHEMA_ID,
        FormulaDerivationPackage,
    )

    if payload.get("schema_id") != FORMULA_DERIVATION_PACKAGE_SCHEMA_ID:
        raise ValidationError("formula derivation package schema changed")
    require_zero_authority(payload)
    validate_semantic_digest(payload)
    package = FormulaDerivationPackage.from_dict(payload)
    if package.to_dict() != dict(payload):
        raise ValidationError("formula derivation package does not round-trip canonically")


__all__ = [
    "attach_semantic_digest",
    "require_digest",
    "require_exact_keys",
    "require_field_labels",
    "require_mapping",
    "require_sequence",
    "require_text",
    "require_zero_authority",
    "validate_formula_computation_graph",
    "validate_formula_derivation_package",
    "validate_semantic_digest",
]
