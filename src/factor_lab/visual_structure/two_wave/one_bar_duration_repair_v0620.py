"""v0.6.20 exact one-native-bar duration-boundary repair.

This component starts from the v0.6.18 qualification policy and changes only
the role of two *exact* duration-boundary cases:

- ``short_leg`` is diagnostic rather than hard when min_leg == 3;
- ``short_cycle`` is diagnostic rather than hard when min_cycle == 11.

More severe duration failures and every other v0.6.18 hard reason remain hard.
The rule is single-view and causal; cross-offset evidence is not an input.
"""
from __future__ import annotations

import copy
from typing import Sequence

from .duration_geometry_decomposition_v0619 import duration_metrics
from .path_gate_demotion_v0618 import qualify_published_raw_identity_v0618
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_one_bar_duration_repair@0.6.20"
BOUNDARY_REASONS = frozenset({"short_leg", "short_cycle"})
LONG_SPAN_SAFETY_REASONS = frozenset(
    {"long_cycle", "long_pair", "too_many_observed_days", "wall_span_too_long"}
)


def v0620_hard_reasons(
    v0618_hard_reasons: Sequence[str],
    five_raw_occurrence_bars: Sequence[int],
) -> tuple[list[str], dict]:
    """Return hard reasons after only the two preregistered exact-boundary demotions."""
    old = [str(x) for x in v0618_hard_reasons]
    metrics = duration_metrics(five_raw_occurrence_bars)
    demote_short_leg = "short_leg" in old and int(metrics["min_leg"]) == 3
    demote_short_cycle = "short_cycle" in old and int(metrics["min_cycle"]) == 11

    new = []
    for reason in old:
        if reason == "short_leg" and demote_short_leg:
            continue
        if reason == "short_cycle" and demote_short_cycle:
            continue
        new.append(reason)

    diagnostics = {
        "min_leg": int(metrics["min_leg"]),
        "min_cycle": int(metrics["min_cycle"]),
        "cycle_duration_ratio": float(metrics["cycle_duration_ratio"]),
        "short_leg_exact_one_bar_boundary_demoted": bool(demote_short_leg),
        "short_cycle_exact_one_bar_boundary_demoted": bool(demote_short_cycle),
    }
    return new, diagnostics


def requalify_v0618(
    v0618_control: dict,
    five_raw_occurrence_bars: Sequence[int],
) -> dict:
    """Apply the exact one-bar repair to one v0.6.18 result."""
    if "v0618_hard_rejection_reasons" not in v0618_control:
        raise ValueError("v0.6.18 hard reasons required")
    old = [str(x) for x in v0618_control["v0618_hard_rejection_reasons"]]
    if bool(v0618_control.get("scale_qualified")) and old:
        raise ValueError("inconsistent v0.6.18 qualified result")
    if not bool(v0618_control.get("scale_qualified")) and not old:
        raise ValueError("inconsistent v0.6.18 rejected result")

    new, diagnostics = v0620_hard_reasons(old, five_raw_occurrence_bars)
    if any(reason not in old for reason in new):
        raise AssertionError("v0.6.20 may not add a hard reason")

    # Frozen safety invariants.
    if any(reason in old for reason in LONG_SPAN_SAFETY_REASONS) and not any(
        reason in new for reason in LONG_SPAN_SAFETY_REASONS
    ):
        raise AssertionError("v0.6.20 may not demote a long-span safety reason")
    if "cycle_duration_mismatch" in old and "cycle_duration_mismatch" not in new:
        raise AssertionError("v0.6.20 may not demote cycle_duration_mismatch")
    if "short_leg" in old and diagnostics["min_leg"] <= 2 and "short_leg" not in new:
        raise AssertionError("v0.6.20 may not demote severe short_leg")
    if "short_cycle" in old and diagnostics["min_cycle"] <= 10 and "short_cycle" not in new:
        raise AssertionError("v0.6.20 may not demote severe short_cycle")

    out = copy.deepcopy(v0618_control)
    out["schema"] = SCHEMA
    out["upstream_control_schema"] = v0618_control.get("schema")
    out["v0618_hard_rejection_reasons"] = old
    out["v0620_hard_rejection_reasons"] = new
    out["one_bar_duration_boundary_diagnostics"] = diagnostics
    out["scale_qualified"] = not new
    out["future_outcome_used"] = False
    out["trade_authority"] = False
    return out


def qualify_published_raw_identity_v0620(
    phase: str,
    five_raw_occurrence_bars: Sequence[int],
    publishing_confirmation_bar: int,
    bars: Sequence[dict],
    cfg: MaturityConfig | None = None,
) -> dict:
    """Run v0.6.18 then apply the frozen v0.6.20 exact-boundary repair."""
    control = qualify_published_raw_identity_v0618(
        phase,
        five_raw_occurrence_bars,
        publishing_confirmation_bar,
        bars,
        cfg=cfg,
    )
    return requalify_v0618(control, five_raw_occurrence_bars)
