"""v0.6.18 qualification policy: demote resolution-dependent path gates.

The upstream financial identity, raw projection and all non-path qualification
rules remain frozen.  This module only changes the *role* of two legacy native
5m measurements: ``inefficient_leg`` and ``jump_dominated_leg`` remain recorded
as diagnostics but no longer veto same-scale qualification.
"""
from __future__ import annotations

import copy
from typing import Sequence

from .published_identity_qualification_v066 import qualify_published_raw_identity
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_path_gate_demotion@0.6.18"
DEMOTED_PATH_REASONS = frozenset({"inefficient_leg", "jump_dominated_leg"})


def v0618_hard_reasons(v054_hard_reasons: Sequence[str]) -> list[str]:
    """Remove exactly the two preregistered resolution-dependent path reasons."""
    return [str(reason) for reason in v054_hard_reasons if str(reason) not in DEMOTED_PATH_REASONS]


def requalify_v066_control(control: dict) -> dict:
    """Apply the frozen v0.6.18 role change to one v0.6.6 qualification result."""
    if "v054_hard_rejection_reasons" not in control:
        raise ValueError("v0.6.6 control hard reasons required")
    old_hard = [str(x) for x in control["v054_hard_rejection_reasons"]]
    new_hard = v0618_hard_reasons(old_hard)

    # The candidate is monotone by construction: it cannot invent a rejection.
    if not bool(control.get("scale_qualified")) and not old_hard:
        raise ValueError("inconsistent v0.6.6 control qualification")
    if bool(control.get("scale_qualified")) and old_hard:
        raise ValueError("inconsistent v0.6.6 control hard reasons")
    if any(reason not in old_hard for reason in new_hard):
        raise AssertionError("candidate may not add a hard reason")

    out = copy.deepcopy(control)
    out["schema"] = SCHEMA
    out["upstream_control_schema"] = control.get("schema")
    out["v054_hard_rejection_reasons"] = old_hard
    out["v0618_hard_rejection_reasons"] = new_hard
    out["demoted_path_diagnostics"] = {
        reason: reason in old_hard for reason in sorted(DEMOTED_PATH_REASONS)
    }
    out["demoted_path_reason_count"] = sum(reason in old_hard for reason in DEMOTED_PATH_REASONS)
    out["scale_qualified"] = not new_hard
    out["future_outcome_used"] = False
    out["trade_authority"] = False
    return out


def qualify_published_raw_identity_v0618(
    phase: str,
    five_raw_occurrence_bars: Sequence[int],
    publishing_confirmation_bar: int,
    bars: Sequence[dict],
    cfg: MaturityConfig | None = None,
) -> dict:
    """Run frozen v0.6.6 measurement, then demote only the two path vetoes."""
    control = qualify_published_raw_identity(
        phase,
        five_raw_occurrence_bars,
        publishing_confirmation_bar,
        bars,
        cfg=cfg,
    )
    return requalify_v066_control(control)
