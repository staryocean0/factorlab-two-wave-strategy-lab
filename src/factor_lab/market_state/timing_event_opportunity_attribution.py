# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportImplicitStringConcatenation=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Event-backed opportunity capture and M/F/B/R attribution for timing tools.

This module closes two holes left by aggregate timing scorecards:

* capture and recall must be recomputed from one row per market opportunity,
  rather than trusted as adapter-supplied ratios;
* the old F-R gap is split into the hindsight family-routing gap and the
  current-versus-best-registered-static-parameter gap.

Every ceiling is diagnostic hindsight evidence.  Nothing in this module has
signal, routing, parameter-selection, or production authority.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final[str] = "market_state_timing_event_opportunity_attribution@1.0"
PERIOD_ROLES: Final[frozenset[str]] = frozenset(
    {"development", "repeat_audit", "aggregate_blackbox"}
)
SIDES: Final[frozenset[str]] = frozenset({"up", "down"})

OPPORTUNITY_COLUMNS: Final[tuple[str, ...]] = (
    "period",
    "period_role",
    "scale_id",
    "state_cell_id",
    "opportunity_id",
    "opportunity_side",
    "start_timestamp",
    "extreme_timestamp",
    "end_exclusive",
    "opportunity_size_log",
    "opportunity_bar_count",
    "strategy_signal_independent",
    "diagnostic_only",
)
CAPTURE_COLUMNS: Final[tuple[str, ...]] = (
    "candidate_id",
    "opportunity_id",
    "captured_supply_log",
    "candidate_same_side_bar_count",
    "candidate_opposite_side_bar_count",
    "candidate_net_log_value_on_event",
    "first_capture_timestamp",
    "first_capture_remaining_fraction",
)
CLAIM_COLUMNS: Final[tuple[str, ...]] = (
    "candidate_id",
    "period",
    "period_role",
    "scale_id",
    "state_cell_id",
    "claim_id",
    "claim_side",
    "start_timestamp",
    "end_exclusive",
    "active_bar_count",
    "net_log_value",
    "matched_same_side_opportunity_count",
    "matched_opportunity_ids_json",
    "matched_opportunity_supply_log",
)
MFBR_COLUMNS: Final[tuple[str, ...]] = (
    "candidate_id",
    "period",
    "period_role",
    "scale_id",
    "state_cell_id",
    "opportunity_side",
    "elapsed_years",
    "market_scale_oracle_net_value_per_year",
    "tool_family_oracle_net_value_per_year",
    "best_registered_static_net_value_per_year",
    "best_registered_static_candidate_id",
    "candidate_realized_net_value_per_year",
    "registered_fixed_candidate_count",
    "registered_family_digest",
    "family_registered_before_evaluation",
    "candidate_in_registered_family",
    "lookahead_only",
    "production_authority",
)


def timing_event_opportunity_attribution_contract() -> dict[str, object]:
    """Return the reusable evidence and authority contract."""

    return {
        "schema_id": SCHEMA_ID,
        "infrastructure_owner": "independent_bidirectional_timing_strategy_middle_platform",
        "authority": "evaluation_only_not_signal_route_parameter_or_production_authority",
        "event_evidence_rule": {
            "one_strategy_independent_row_per_market_opportunity": True,
            "one_candidate_row_per_market_opportunity": True,
            "captured_and_missed_supply_recomputed_from_raw_rows": True,
            "candidate_claims_without_same_side_opportunity_reported_separately": True,
            "candidate_claim_matches_recomputed_from_event_rows": True,
            "up_and_down_never_netted": True,
            "opportunity_layer_has_no_performance_pass_fail": True,
        },
        "nested_value_identity": (
            "R=M-(M-F)-(F-B)-(B-R); "
            "M=market, F=tool-family action oracle, B=best registered static, R=current"
        ),
        "weak_period_axes": [
            "market_supply_change",
            "tool_architecture_gap_change",
            "family_routing_gap_change",
            "current_static_parameter_gap_change",
        ],
        "optimality_authority_rule": {
            "unregistered_parameter_family_forbids_parameter_optimality_claim": True,
            "best_registered_static_is_period_hindsight_only": True,
            "tool_family_oracle_is_hindsight_only": True,
            "global_optimality_claim_always_forbidden": True,
            "fresh_generalization_requires_unconsumed_period": True,
        },
        "economic_capture_thresholds": "forbidden",
        "production_authority": False,
    }


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], *, name: str) -> None:
    missing = set(columns).difference(frame.columns)
    if missing:
        raise ValidationError(f"{name} missing columns: {sorted(missing)}")


def validate_event_opportunity_ledger(opportunities: pd.DataFrame) -> None:
    """Validate the raw, direction-explicit market opportunity universe."""

    _require_columns(opportunities, OPPORTUNITY_COLUMNS, name="event opportunity ledger")
    if opportunities.empty:
        raise ValidationError("event opportunity ledger must not be empty")
    if opportunities["opportunity_id"].astype(str).duplicated().any():
        raise ValidationError("opportunity_id must be globally unique")
    if not set(opportunities["period_role"].astype(str)).issubset(PERIOD_ROLES):
        raise ValidationError("unsupported opportunity period_role")
    if not set(opportunities["opportunity_side"].astype(str)).issubset(SIDES):
        raise ValidationError("opportunity_side must remain up/down")
    for column in ("period", "scale_id", "state_cell_id", "opportunity_id"):
        if opportunities[column].astype(str).str.strip().eq("").any():
            raise ValidationError(f"{column} must not be empty")
    start = pd.to_datetime(opportunities["start_timestamp"], errors="coerce", utc=True)
    extreme = pd.to_datetime(opportunities["extreme_timestamp"], errors="coerce", utc=True)
    end = pd.to_datetime(opportunities["end_exclusive"], errors="coerce", utc=True)
    if start.isna().any() or extreme.isna().any() or end.isna().any():
        raise ValidationError("opportunity timestamps must be parseable")
    if not (extreme.ge(start) & extreme.lt(end) & end.gt(start)).all():
        raise ValidationError("opportunity timestamps violate start <= extreme < end")
    numeric = opportunities[["opportunity_size_log", "opportunity_bar_count"]].apply(
        pd.to_numeric, errors="coerce"
    )
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(float)).all():
        raise ValidationError("opportunity size and bars must be finite")
    if numeric["opportunity_size_log"].le(0.0).any():
        raise ValidationError("opportunity_size_log must be positive")
    bars = numeric["opportunity_bar_count"].to_numpy(float)
    if np.any(bars < 1.0) or not np.array_equal(bars, bars.astype(int)):
        raise ValidationError("opportunity_bar_count must be a positive integer")
    if not opportunities["strategy_signal_independent"].astype(bool).all():
        raise ValidationError("market opportunity events must be strategy independent")
    if not opportunities["diagnostic_only"].astype(bool).all():
        raise ValidationError("ex-post opportunity events must remain diagnostic-only")


def validate_event_capture_ledger(
    opportunities: pd.DataFrame,
    captures: pd.DataFrame,
    *,
    numerical_tolerance: float = 1e-10,
) -> None:
    """Require a complete candidate x opportunity matrix and reconcile it."""

    validate_event_opportunity_ledger(opportunities)
    _require_columns(captures, CAPTURE_COLUMNS, name="event capture ledger")
    if captures.empty:
        raise ValidationError("event capture ledger must not be empty")
    if captures[["candidate_id", "opportunity_id"]].astype(str).duplicated().any():
        raise ValidationError("candidate/opportunity capture rows must be unique")
    if captures["candidate_id"].astype(str).str.strip().eq("").any():
        raise ValidationError("candidate_id must not be empty")
    expected_ids = set(opportunities["opportunity_id"].astype(str))
    for candidate_id, local in captures.groupby("candidate_id", sort=False):
        actual_ids = set(local["opportunity_id"].astype(str))
        if actual_ids != expected_ids:
            missing = sorted(expected_ids.difference(actual_ids))
            extra = sorted(actual_ids.difference(expected_ids))
            raise ValidationError(
                f"candidate {candidate_id} does not cover the exact opportunity universe; "
                f"missing={missing[:5]}, extra={extra[:5]}"
            )
    joined = captures.merge(
        opportunities[["opportunity_id", "opportunity_size_log", "opportunity_bar_count", "start_timestamp", "end_exclusive"]],
        on="opportunity_id",
        how="left",
        validate="many_to_one",
    )
    numeric_columns = [
        "captured_supply_log",
        "candidate_same_side_bar_count",
        "candidate_opposite_side_bar_count",
        "candidate_net_log_value_on_event",
        "first_capture_remaining_fraction",
        "opportunity_size_log",
        "opportunity_bar_count",
    ]
    numeric = joined[numeric_columns].apply(pd.to_numeric, errors="coerce")
    finite_columns = [
        "captured_supply_log",
        "candidate_same_side_bar_count",
        "candidate_opposite_side_bar_count",
        "candidate_net_log_value_on_event",
        "opportunity_size_log",
        "opportunity_bar_count",
    ]
    if numeric[finite_columns].isna().any().any() or not np.isfinite(
        numeric[finite_columns].to_numpy(float)
    ).all():
        raise ValidationError("capture metrics must be finite")
    if numeric["captured_supply_log"].lt(-numerical_tolerance).any():
        raise ValidationError("captured supply cannot be negative")
    if (
        numeric["captured_supply_log"]
        > numeric["opportunity_size_log"] + numerical_tolerance
    ).any():
        raise ValidationError("captured supply cannot exceed event supply")
    same = numeric["candidate_same_side_bar_count"].to_numpy(float)
    opposite = numeric["candidate_opposite_side_bar_count"].to_numpy(float)
    event_bars = numeric["opportunity_bar_count"].to_numpy(float)
    for values, label in ((same, "same-side"), (opposite, "opposite-side")):
        if np.any(values < 0.0) or not np.array_equal(values, values.astype(int)):
            raise ValidationError(f"{label} bar count must be a non-negative integer")
    if np.any(same + opposite > event_bars):
        raise ValidationError("candidate event bar counts exceed opportunity duration")
    captured = same > 0
    first = pd.to_datetime(joined["first_capture_timestamp"], errors="coerce", utc=True)
    start = pd.to_datetime(joined["start_timestamp"], errors="raise", utc=True)
    end = pd.to_datetime(joined["end_exclusive"], errors="raise", utc=True)
    if first[captured].isna().any() or not (
        first[captured].ge(start[captured]) & first[captured].lt(end[captured])
    ).all():
        raise ValidationError("captured events require an in-event first capture timestamp")
    remaining = numeric["first_capture_remaining_fraction"]
    if remaining[captured].isna().any() or not remaining[captured].between(0.0, 1.0).all():
        raise ValidationError("captured events require a remaining fraction in [0, 1]")
    if first[~captured].notna().any() or remaining[~captured].notna().any():
        raise ValidationError("missed events cannot invent first-capture evidence")
    if numeric.loc[~captured, "captured_supply_log"].abs().gt(numerical_tolerance).any():
        raise ValidationError("missed events must have zero captured supply")


def summarize_event_opportunity_capture(
    opportunities: pd.DataFrame,
    captures: pd.DataFrame,
    *,
    group_columns: Sequence[str] = (
        "candidate_id",
        "period",
        "period_role",
        "scale_id",
        "state_cell_id",
        "opportunity_side",
    ),
    numerical_tolerance: float = 1e-10,
) -> pd.DataFrame:
    """Recompute captured, partial, and missed opportunity supply from events."""

    validate_event_capture_ledger(
        opportunities,
        captures,
        numerical_tolerance=numerical_tolerance,
    )
    joined = captures.merge(opportunities, on="opportunity_id", how="left", validate="many_to_one")
    joined["captured_by_position"] = pd.to_numeric(
        joined["candidate_same_side_bar_count"], errors="raise"
    ).gt(0)
    supply = pd.to_numeric(joined["opportunity_size_log"], errors="raise")
    captured_supply = pd.to_numeric(joined["captured_supply_log"], errors="raise")
    joined["capture_status"] = np.where(
        ~joined["captured_by_position"],
        "missed",
        np.where((supply - captured_supply).abs().le(numerical_tolerance), "full", "partial"),
    )
    rows: list[dict[str, object]] = []
    for keys, local in joined.groupby(list(group_columns), sort=True, dropna=False):
        normalized = keys if isinstance(keys, tuple) else (keys,)
        event_supply = pd.to_numeric(local["opportunity_size_log"], errors="raise")
        local_captured_supply = pd.to_numeric(local["captured_supply_log"], errors="raise")
        captured = local["captured_by_position"].astype(bool)
        remaining = pd.to_numeric(
            local.loc[captured, "first_capture_remaining_fraction"], errors="coerce"
        ).dropna()
        status = local["capture_status"].value_counts()
        total_supply = float(event_supply.sum())
        caught_supply = float(local_captured_supply.sum())
        rows.append(
            {
                **dict(zip(group_columns, normalized, strict=True)),
                "market_opportunity_count": int(len(local)),
                "market_opportunity_supply": total_supply,
                "market_opportunity_bars": int(
                    pd.to_numeric(local["opportunity_bar_count"], errors="raise").sum()
                ),
                "captured_opportunity_count": int(captured.sum()),
                "fully_captured_opportunity_count": int(status.get("full", 0)),
                "partially_captured_opportunity_count": int(status.get("partial", 0)),
                "missed_opportunity_count": int(status.get("missed", 0)),
                "captured_opportunity_supply": caught_supply,
                "missed_opportunity_supply": total_supply - caught_supply,
                "opportunity_recall_rate": float(captured.mean()),
                "opportunity_capture_rate": caught_supply / total_supply,
                "mean_first_capture_remaining_fraction": (
                    float(remaining.mean()) if len(remaining) else np.nan
                ),
                "candidate_same_side_bar_count": int(
                    pd.to_numeric(local["candidate_same_side_bar_count"], errors="raise").sum()
                ),
                "candidate_opposite_side_bar_count": int(
                    pd.to_numeric(local["candidate_opposite_side_bar_count"], errors="raise").sum()
                ),
                "candidate_net_log_value_on_opportunities": float(
                    pd.to_numeric(local["candidate_net_log_value_on_event"], errors="raise").sum()
                ),
                "ledger_status": "verified",
                "performance_pass_fail_semantics": "forbidden",
                "economic_capture_threshold_used": False,
            }
        )
    return pd.DataFrame(rows)


def _parse_matched_opportunity_ids(value: object) -> tuple[str, ...]:
    try:
        decoded = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise ValidationError("matched_opportunity_ids_json must be a JSON string list") from exc
    if not isinstance(decoded, list) or not all(
        isinstance(item, str) and item.strip() for item in decoded
    ):
        raise ValidationError("matched_opportunity_ids_json must contain non-empty strings")
    normalized = tuple(str(item) for item in decoded)
    if len(set(normalized)) != len(normalized):
        raise ValidationError("matched opportunity ids must be unique inside one claim")
    return normalized


def validate_candidate_claim_ledger(
    claims: pd.DataFrame,
    opportunities: pd.DataFrame | None = None,
    captures: pd.DataFrame | None = None,
    *,
    numerical_tolerance: float = 1e-10,
) -> None:
    """Validate candidate-owned lifecycles, including unmatched false claims."""

    _require_columns(claims, CLAIM_COLUMNS, name="candidate claim ledger")
    if claims.empty:
        raise ValidationError("candidate claim ledger must not be empty")
    if claims[["candidate_id", "claim_id"]].astype(str).duplicated().any():
        raise ValidationError("candidate claim ids must be unique")
    if not set(claims["period_role"].astype(str)).issubset(PERIOD_ROLES):
        raise ValidationError("unsupported claim period_role")
    if not set(claims["claim_side"].astype(str)).issubset(SIDES):
        raise ValidationError("claim_side must remain up/down")
    start = pd.to_datetime(claims["start_timestamp"], errors="coerce", utc=True)
    end = pd.to_datetime(claims["end_exclusive"], errors="coerce", utc=True)
    if start.isna().any() or end.isna().any() or not end.gt(start).all():
        raise ValidationError("claim timestamps must satisfy start < end")
    numeric = claims[
        [
            "active_bar_count",
            "net_log_value",
            "matched_same_side_opportunity_count",
            "matched_opportunity_supply_log",
        ]
    ].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(float)).all():
        raise ValidationError("claim metrics must be finite")
    for column in ("active_bar_count", "matched_same_side_opportunity_count"):
        values = numeric[column].to_numpy(float)
        minimum = 1.0 if column == "active_bar_count" else 0.0
        if np.any(values < minimum) or not np.array_equal(values, values.astype(int)):
            raise ValidationError(f"{column} must be an integer >= {minimum:g}")
    if numeric["matched_opportunity_supply_log"].lt(0.0).any():
        raise ValidationError("matched opportunity supply cannot be negative")
    parsed_ids = claims["matched_opportunity_ids_json"].map(_parse_matched_opportunity_ids)
    parsed_counts = parsed_ids.map(len).to_numpy(int)
    declared_counts = numeric["matched_same_side_opportunity_count"].to_numpy(int)
    if not np.array_equal(parsed_counts, declared_counts):
        raise ValidationError("matched opportunity ids do not reconcile to the declared count")
    unmatched = numeric["matched_same_side_opportunity_count"].eq(0)
    if numeric.loc[unmatched, "matched_opportunity_supply_log"].ne(0.0).any():
        raise ValidationError("unmatched claims cannot report matched opportunity supply")
    if (opportunities is None) != (captures is None):
        raise ValidationError("claim-to-event reconciliation requires opportunities and captures together")
    if opportunities is None or captures is None:
        return

    validate_event_capture_ledger(opportunities, captures, numerical_tolerance=numerical_tolerance)
    opportunity_index = opportunities.set_index("opportunity_id", verify_integrity=True)
    capture_index = captures.set_index(
        ["candidate_id", "opportunity_id"], verify_integrity=True
    )
    for location, claim in claims.reset_index(drop=True).iterrows():
        ids = parsed_ids.iloc[int(location)]
        claim_start = pd.to_datetime(claim["start_timestamp"], errors="raise", utc=True)
        claim_end = pd.to_datetime(claim["end_exclusive"], errors="raise", utc=True)
        recomputed_supply = 0.0
        for opportunity_id in ids:
            if opportunity_id not in opportunity_index.index:
                raise ValidationError("claim references an unknown opportunity id")
            event = opportunity_index.loc[opportunity_id]
            if str(event["opportunity_side"]) != str(claim["claim_side"]):
                raise ValidationError("claim matched an opposite-side opportunity")
            for column in ("period", "period_role", "scale_id", "state_cell_id"):
                if str(event[column]) != str(claim[column]):
                    raise ValidationError(f"claim/event {column} does not match")
            event_start = pd.to_datetime(event["start_timestamp"], errors="raise", utc=True)
            event_end = pd.to_datetime(event["end_exclusive"], errors="raise", utc=True)
            if not (event_start < claim_end and event_end > claim_start):
                raise ValidationError("claim and matched opportunity do not overlap in time")
            capture_key = (str(claim["candidate_id"]), opportunity_id)
            if capture_key not in capture_index.index:
                raise ValidationError("claim lacks its candidate/opportunity capture row")
            captured_supply = float(capture_index.loc[capture_key, "captured_supply_log"])
            if captured_supply <= numerical_tolerance:
                raise ValidationError("claim cannot match an opportunity the candidate did not capture")
            recomputed_supply += captured_supply
        declared_supply = float(claim["matched_opportunity_supply_log"])
        if not np.isclose(
            recomputed_supply,
            declared_supply,
            rtol=0.0,
            atol=numerical_tolerance,
        ):
            raise ValidationError("claim matched opportunity supply does not replay")


def summarize_candidate_claims(
    claims: pd.DataFrame,
    opportunities: pd.DataFrame | None = None,
    captures: pd.DataFrame | None = None,
    *,
    group_columns: Sequence[str] = (
        "candidate_id",
        "period",
        "period_role",
        "scale_id",
        "state_cell_id",
        "claim_side",
    ),
) -> pd.DataFrame:
    """Expose profitable, losing, and unmatched candidate lifecycles."""

    validate_candidate_claim_ledger(claims, opportunities, captures)
    rows: list[dict[str, object]] = []
    for keys, local in claims.groupby(list(group_columns), sort=True, dropna=False):
        normalized = keys if isinstance(keys, tuple) else (keys,)
        net = pd.to_numeric(local["net_log_value"], errors="raise")
        matched = pd.to_numeric(
            local["matched_same_side_opportunity_count"], errors="raise"
        ).gt(0)
        unmatched_net = net.loc[~matched]
        rows.append(
            {
                **dict(zip(group_columns, normalized, strict=True)),
                "claim_count": int(len(local)),
                "matched_claim_count": int(matched.sum()),
                "unmatched_claim_count": int((~matched).sum()),
                "profitable_claim_count": int(net.gt(0.0).sum()),
                "losing_claim_count": int(net.lt(0.0).sum()),
                "claim_net_log_value": float(net.sum()),
                "mean_claim_net_log_value": float(net.mean()),
                "unmatched_claim_net_log_value": float(unmatched_net.sum()),
                "unmatched_claim_loss_log": float(-unmatched_net.clip(upper=0.0).sum()),
                "matched_opportunity_supply_log": float(
                    pd.to_numeric(local["matched_opportunity_supply_log"], errors="raise").sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def validate_mfbr_ledger(
    ledger: pd.DataFrame,
    *,
    numerical_tolerance: float = 1e-10,
) -> None:
    """Validate M >= F >= B >= R under a registered fixed family."""

    _require_columns(ledger, MFBR_COLUMNS, name="M/F/B/R ledger")
    if ledger.empty:
        raise ValidationError("M/F/B/R ledger must not be empty")
    identity = [
        "candidate_id",
        "period",
        "scale_id",
        "state_cell_id",
        "opportunity_side",
    ]
    if ledger[identity].astype(str).duplicated().any():
        raise ValidationError("M/F/B/R identity rows must be unique")
    if not set(ledger["period_role"].astype(str)).issubset(PERIOD_ROLES):
        raise ValidationError("unsupported M/F/B/R period_role")
    if not set(ledger["opportunity_side"].astype(str)).issubset(SIDES):
        raise ValidationError("M/F/B/R side must remain up/down")
    numeric_columns = [
        "elapsed_years",
        "market_scale_oracle_net_value_per_year",
        "tool_family_oracle_net_value_per_year",
        "best_registered_static_net_value_per_year",
        "candidate_realized_net_value_per_year",
        "registered_fixed_candidate_count",
    ]
    numeric = ledger[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(float)).all():
        raise ValidationError("M/F/B/R values must be finite")
    if numeric["elapsed_years"].le(0.0).any():
        raise ValidationError("elapsed_years must be positive")
    counts = numeric["registered_fixed_candidate_count"].to_numpy(float)
    if np.any(counts < 1.0) or not np.array_equal(counts, counts.astype(int)):
        raise ValidationError("registered fixed candidate count must be a positive integer")
    market = numeric["market_scale_oracle_net_value_per_year"]
    family = numeric["tool_family_oracle_net_value_per_year"]
    best = numeric["best_registered_static_net_value_per_year"]
    realized = numeric["candidate_realized_net_value_per_year"]
    if market.lt(-numerical_tolerance).any() or family.lt(-numerical_tolerance).any():
        raise ValidationError("M and F cannot be negative because flat is available")
    if (family > market + numerical_tolerance).any():
        raise ValidationError("tool family oracle cannot exceed market oracle")
    if (best > family + numerical_tolerance).any():
        raise ValidationError("best registered static cannot exceed tool family oracle")
    if (realized > best + numerical_tolerance).any():
        raise ValidationError("current candidate cannot exceed best static when it belongs to the family")
    if not ledger["candidate_in_registered_family"].astype(bool).all():
        raise ValidationError("current candidate must be included in the registered family")
    if ledger["registered_family_digest"].astype(str).str.strip().eq("").any():
        raise ValidationError("registered family digest must not be empty")
    if not ledger["lookahead_only"].astype(bool).all():
        raise ValidationError("M/F/B are hindsight diagnostics and must be marked lookahead-only")
    if ledger["production_authority"].astype(bool).any():
        raise ValidationError("M/F/B/R evidence cannot gain production authority")


def summarize_mfbr_attribution(
    ledger: pd.DataFrame,
    *,
    numerical_tolerance: float = 1e-10,
) -> pd.DataFrame:
    """Split old F-R into family-routing and fixed-parameter mismatch gaps."""

    validate_mfbr_ledger(ledger, numerical_tolerance=numerical_tolerance)
    rows: list[dict[str, object]] = []
    for row in ledger.itertuples(index=False):
        market = float(row.market_scale_oracle_net_value_per_year)
        family = float(row.tool_family_oracle_net_value_per_year)
        best = float(row.best_registered_static_net_value_per_year)
        realized = float(row.candidate_realized_net_value_per_year)
        architecture_gap = market - family
        family_routing_gap = family - best
        current_parameter_gap = best - realized
        count = int(row.registered_fixed_candidate_count)
        registered_before = bool(row.family_registered_before_evaluation)
        if count < 2 or not registered_before:
            status = "not_testable_without_preregistered_parameter_family"
        elif current_parameter_gap <= numerical_tolerance:
            status = "matches_period_hindsight_best_within_registered_static_family"
        else:
            status = "registered_static_parameter_mismatch_space_present"
        rows.append(
            {
                **row._asdict(),
                "tool_architecture_gap_per_year": architecture_gap,
                "family_routing_gap_per_year": family_routing_gap,
                "current_static_parameter_gap_per_year": current_parameter_gap,
                "value_conservation_error": realized
                - (market - architecture_gap - family_routing_gap - current_parameter_gap),
                "parameter_optimality_status": status,
                "best_static_is_period_hindsight_only": True,
                "global_optimality_claim_permitted": False,
                "parameter_authority": False,
            }
        )
    return pd.DataFrame(rows)


def diagnose_mfbr_period_change(
    ledger: pd.DataFrame,
    *,
    reference_period: str,
    numerical_tolerance: float = 1e-10,
) -> pd.DataFrame:
    """Decompose each period's realized change against one explicit reference."""

    nested = summarize_mfbr_attribution(ledger, numerical_tolerance=numerical_tolerance)
    rows: list[dict[str, object]] = []
    groups = ["candidate_id", "scale_id", "state_cell_id", "opportunity_side"]
    for keys, local in nested.groupby(groups, sort=True):
        reference_rows = local.loc[local["period"].astype(str).eq(reference_period)]
        if len(reference_rows) != 1:
            raise ValidationError(f"one explicit reference period is required for {keys}")
        reference = reference_rows.iloc[0]
        for row in local.loc[~local["period"].astype(str).eq(reference_period)].itertuples(index=False):
            realized_change = float(row.candidate_realized_net_value_per_year) - float(
                reference["candidate_realized_net_value_per_year"]
            )
            market_contribution = float(row.market_scale_oracle_net_value_per_year) - float(
                reference["market_scale_oracle_net_value_per_year"]
            )
            architecture_contribution = -(
                float(row.tool_architecture_gap_per_year)
                - float(reference["tool_architecture_gap_per_year"])
            )
            routing_contribution = -(
                float(row.family_routing_gap_per_year)
                - float(reference["family_routing_gap_per_year"])
            )
            parameter_contribution = -(
                float(row.current_static_parameter_gap_per_year)
                - float(reference["current_static_parameter_gap_per_year"])
            )
            contributions = {
                "market_supply_decline": market_contribution,
                "tool_architecture_gap_widening": architecture_contribution,
                "family_routing_gap_widening": routing_contribution,
                "current_static_parameter_gap_widening": parameter_contribution,
            }
            if realized_change >= -numerical_tolerance:
                driver = "no_realized_decline"
            else:
                deteriorations = {
                    name: max(0.0, -value) for name, value in contributions.items()
                }
                maximum = max(deteriorations.values())
                leaders = [
                    name
                    for name, value in deteriorations.items()
                    if abs(value - maximum) <= numerical_tolerance
                ]
                driver = leaders[0] if len(leaders) == 1 else "mixed_equal_decline_contributors"
            closure = realized_change - sum(contributions.values())
            rows.append(
                {
                    **dict(zip(groups, keys, strict=True)),
                    "reference_period": reference_period,
                    "evaluation_period": str(row.period),
                    "evaluation_period_role": str(row.period_role),
                    "realized_net_value_change_per_year": realized_change,
                    "market_supply_contribution_per_year": market_contribution,
                    "tool_architecture_contribution_per_year": architecture_contribution,
                    "family_routing_contribution_per_year": routing_contribution,
                    "current_static_parameter_contribution_per_year": parameter_contribution,
                    "dominant_decline_driver": driver,
                    "value_conservation_error": closure,
                    "economic_ratio_threshold_used": False,
                }
            )
    return pd.DataFrame(rows)


__all__ = [
    "CAPTURE_COLUMNS",
    "CLAIM_COLUMNS",
    "MFBR_COLUMNS",
    "OPPORTUNITY_COLUMNS",
    "SCHEMA_ID",
    "diagnose_mfbr_period_change",
    "summarize_candidate_claims",
    "summarize_event_opportunity_capture",
    "summarize_mfbr_attribution",
    "timing_event_opportunity_attribution_contract",
    "validate_candidate_claim_ledger",
    "validate_event_capture_ledger",
    "validate_event_opportunity_ledger",
    "validate_mfbr_ledger",
]
