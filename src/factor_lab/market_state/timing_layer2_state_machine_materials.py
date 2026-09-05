# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Strategy-neutral research materials recovered from historical state machines."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError

MATERIAL_SCHEMA_ID: Final[str] = "timing_layer2_state_machine_research_material@1.0"


def build_causal_ema_log_return_velocity(
    price: pd.Series,
    *,
    halflife: float = 4.0,
) -> pd.Series:
    """Recover the continuous EMA velocity axis without its K buckets."""

    numeric = pd.to_numeric(price, errors="raise").astype(float)
    if numeric.empty or numeric.isna().any() or bool((numeric <= 0.0).any()):
        raise ValidationError("EMA velocity requires finite positive prices")
    if halflife <= 0.0:
        raise ValidationError("EMA velocity halflife must be positive")
    log_price = pd.Series(np.log(numeric.to_numpy(float)), index=numeric.index)
    result = cast(
        pd.Series,
        log_price.diff().ewm(halflife=halflife, min_periods=2).mean().shift(1),
    )
    result.name = f"ema_log_return_velocity_h{halflife:g}_t_minus_1"
    result.attrs["timing_layer_contract"] = {
        "schema_id": MATERIAL_SCHEMA_ID,
        "source_state_machine": "crash_rebound_current_best",
        "thresholds_migrated": False,
        "k_mapping_migrated": False,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return result


def build_local_quadratic_endpoint_kinematics(
    close: pd.Series,
    *,
    window_bars: int,
) -> pd.DataFrame:
    """Recover causal endpoint velocity/acceleration from FDA state machines."""

    numeric = pd.to_numeric(close, errors="raise").astype(float)
    if numeric.empty or numeric.isna().any() or bool((numeric <= 0.0).any()):
        raise ValidationError("local quadratic kinematics requires finite positive closes")
    if window_bars < 5:
        raise ValidationError("local quadratic kinematics requires at least five bars")
    values = np.log(numeric.to_numpy(float))
    x = np.arange(-(window_bars - 1), 1, dtype=float)
    design = np.column_stack((np.ones(window_bars), x, x * x))
    inverse = np.linalg.pinv(design)
    velocity = np.full(len(values), np.nan, dtype=float)
    acceleration = np.full(len(values), np.nan, dtype=float)
    if len(values) >= window_bars:
        velocity[window_bars - 1 :] = np.convolve(values, inverse[1][::-1], mode="valid")
        acceleration[window_bars - 1 :] = np.convolve(values, (2.0 * inverse[2])[::-1], mode="valid")
    result = pd.DataFrame(
        {
            f"local_quadratic_velocity_w{window_bars}": velocity,
            f"local_quadratic_acceleration_w{window_bars}": acceleration,
        },
        index=numeric.index,
    )
    result.attrs["timing_layer_contract"] = {
        "schema_id": MATERIAL_SCHEMA_ID,
        "source_state_machines": ["explosive_layer_v3", "fda_multiscale_channel"],
        "sign_gate_migrated": False,
        "entry_or_exit_migrated": False,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return result


def project_formula_native_attribute_materials(
    derivation_package: Mapping[str, object],
) -> dict[str, object]:
    """Project formula-native continuous attributes and exclude state templates."""

    if derivation_package.get("schema_id") != "market_state_formula_derivation_package@1.0":
        raise ValidationError("formula material projection requires a V3 derivation package")
    for authority in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
    ):
        if derivation_package.get(authority) is not False:
            raise ValidationError("formula material source overclaims authority")
    raw = derivation_package.get("formula_native_attributes")
    if not isinstance(raw, list) or not raw:
        raise ValidationError("formula derivation package has no native attributes")
    attributes: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValidationError("formula-native attribute must be an object")
        if item.get("evidence_level") != "structural_dependency":
            raise ValidationError("formula-native material must remain structural evidence")
        if item.get("availability") != "after_close":
            raise ValidationError("formula-native material availability drifted")
        attributes.append(dict(cast(Mapping[str, object], item)))
    return {
        "schema_id": MATERIAL_SCHEMA_ID,
        "material_kind": "formula_native_continuous_attributes",
        "source_package_id": derivation_package.get("package_id"),
        "source_semantic_digest": derivation_package.get("semantic_digest"),
        "attribute_count": len(attributes),
        "attributes": attributes,
        "interaction_state_machine_templates_migrated": False,
        "parameter_contrasts_migrated": False,
        "strategy_selection_authority": False,
        "routing_authority": False,
        "production_authority": False,
    }


__all__ = [
    "MATERIAL_SCHEMA_ID",
    "build_causal_ema_log_return_velocity",
    "build_local_quadratic_endpoint_kinematics",
    "project_formula_native_attribute_materials",
]
