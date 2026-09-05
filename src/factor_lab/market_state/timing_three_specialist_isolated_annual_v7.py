"""Clean-room annual rebuild primitives for the three-specialist timing sample.

The module deliberately depends on the frozen V4 common-root implementation,
not on any V5/V6/legacy-V7 policy or research artifact.  It provides a
serializable whole-policy specification plus event- and trade-level evidence
needed by one annual research session.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.research.ols_paper_explosive_bucket_battle_v1 import (
    enforce_true_t_plus_one,
)
from factor_lab.market_state.timing_lifecycle_parameter_router import (
    compose_ordered_specialist_claims,
    gate_complete_lifecycle_by_entry_threshold,
)
from factor_lab.market_state.timing_three_bucket_iir_reference_v1 import (
    TimingThreeBucketIIRReferenceSpec,
    aggregate_account_metrics,
    signed_position_ledger,
)
from factor_lab.market_state.timing_three_bucket_iir_reference_v2 import (
    TimingMarketFieldIIRSupplementSpec,
)
from factor_lab.market_state.timing_three_bucket_iir_reference_v4 import (
    TimingSpecialistProgressiveRouteSpec,
    build_three_bucket_iir_reference_v4,
)

SCHEMA_ID: Final[str] = "market_state_timing_three_specialist_isolated_annual_v7@1.0"
COMMON_ROOT_POLICY_ID: Final[str] = "timing_three_bucket_iir_reference_v4"
COMMON_ROOT_POLICY_DIGEST: Final[str] = (
    "sha256:8d256e21c64426369f9a3b721bb727b357eb388a7511ba974132f8cc5ed5f321"
)


def read_sorted_csv_strictly_before(
    path: Path,
    *,
    columns: list[str],
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    """Read a sorted carrier without materializing any post-cutoff market row.

    Pandas chunk readers necessarily parse the remainder of the chunk that
    crosses ``cutoff``.  That is harmless for ordinary backtests, but it does
    not satisfy the annual clean-room contract: the next year's OHLC values
    must not even enter the session process.  This reader inspects only the
    timestamp field of the first boundary row and stops before copying any of
    that row's market values.
    """

    requested = tuple(dict.fromkeys(columns))
    if "timestamp" not in requested:
        raise ValueError("strict annual CSV reads require the timestamp column")
    rows: list[dict[str, str]] = []
    previous: pd.Timestamp | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        available = set(reader.fieldnames or ())
        missing = sorted(set(requested).difference(available))
        if missing:
            raise KeyError(f"strict annual CSV source is missing columns: {missing}")
        for raw in reader:
            timestamp = pd.Timestamp(raw["timestamp"])
            if previous is not None and timestamp < previous:
                raise RuntimeError(f"strict annual CSV source is not sorted: {path}")
            previous = timestamp
            if timestamp >= cutoff:
                break
            rows.append({column: raw[column] for column in requested})
    if not rows:
        raise RuntimeError(f"no rows available before {cutoff.date()}: {path}")
    result = pd.DataFrame.from_records(rows, columns=requested)
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="raise")
    for column in requested:
        if column == "timestamp":
            continue
        normalized = result[column].astype("string").str.strip().str.lower()
        if bool(normalized.isin({"true", "false"}).all()):
            result[column] = normalized.map({"true": True, "false": False}).astype(bool)
            continue
        try:
            result[column] = pd.to_numeric(result[column], errors="raise")
        except (TypeError, ValueError):
            # Preserve genuinely categorical carrier columns exactly as text.
            pass
    if result["timestamp"].duplicated().any() or bool(result["timestamp"].ge(cutoff).any()):
        raise RuntimeError(f"strict annual CSV reader violated cutoff for {path}")
    return result


@dataclass(frozen=True, slots=True)
class IsolatedAnnualPolicySpec:
    """One complete policy reconstructed from the V4 common root."""

    candidate_id: str
    reference_history_days: int = 625
    reference_minimum_days: int = 312
    crash_default_breadth_minimum: float = 0.35
    crash_strict_breadth_minimum: float = 0.40
    paper_default_trend_days: int = 2
    paper_alternate_trend_days: int = 3
    paper_tail_quantile: float = 0.925
    paper_band_heat_minimum: float = 0.0
    paper_signed_path_efficiency_minimum: float = 0.0
    paper_fast_band_change_minimum: float = 0.0
    ols_default_jump_minimum: float = 0.19
    ols_relaxed_jump_minimum: float = 0.14
    ols_band_change_minimum: float = 0.0
    ols_signed_path_efficiency_maximum: float = 0.0
    use_progressive_paper_up: bool = True
    use_progressive_ols_down: bool = True
    ols_prior_20d_return_floor: float | None = None
    residual_long_prior_return_lookback_days: int = 250
    residual_long_prior_return_minimum: float | None = None
    residual_long_recovery_return_lookback_days: int = 20
    residual_long_recovery_return_minimum: float | None = None
    residual_long_highpass_power_heat_maximum: float | None = None
    residual_reference_history_days: int = 625
    residual_reference_minimum_days: int = 312
    residual_variance_ratio_scale_days: float = 4.0
    residual_variance_ratio_quantile: float = 0.8
    residual_path_efficiency_scale_days: float = 8.0
    residual_path_efficiency_quantile: float = 0.5
    residual_highpass_cutoff_days: float = 4.0
    residual_highpass_power_heat_maximum: float = 1.0
    common_root_policy_id: str = COMMON_ROOT_POLICY_ID
    common_root_policy_digest: str = COMMON_ROOT_POLICY_DIGEST
    calendar_identity_used_as_feature: bool = False
    runtime_uses_future: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id cannot be empty")
        if self.common_root_policy_id != COMMON_ROOT_POLICY_ID:
            raise ValueError("isolated policy must be reconstructed from the frozen common root")
        if self.common_root_policy_digest != COMMON_ROOT_POLICY_DIGEST:
            raise ValueError("isolated policy common-root digest drifted")
        if self.calendar_identity_used_as_feature or self.runtime_uses_future:
            raise ValueError("calendar identity or future information entered the policy")
        if self.ols_prior_20d_return_floor is not None and not (
            -0.50 < self.ols_prior_20d_return_floor < 0.0
        ):
            raise ValueError("OLS prior-return floor must be a plausible negative return")
        if self.residual_long_prior_return_lookback_days < 20:
            raise ValueError("residual long prior-return lookback must be at least 20 days")
        if self.residual_long_prior_return_minimum is not None and not (
            -0.80 < self.residual_long_prior_return_minimum < 0.20
        ):
            raise ValueError("residual long prior-return minimum is implausible")
        if self.residual_long_recovery_return_lookback_days < 5:
            raise ValueError("residual long recovery lookback must be at least 5 days")
        if self.residual_long_recovery_return_minimum is not None and not (
            -0.30 < self.residual_long_recovery_return_minimum < 0.30
        ):
            raise ValueError("residual long recovery minimum is implausible")
        if (
            self.residual_long_recovery_return_minimum is not None
            and self.residual_long_prior_return_minimum is None
        ):
            raise ValueError("a recovery release requires an active residual bear guard")
        if self.residual_long_highpass_power_heat_maximum is not None and not (
            -5.0 < self.residual_long_highpass_power_heat_maximum < 5.0
        ):
            raise ValueError("residual long highpass-heat maximum is implausible")
        if self.production_authority:
            raise ValueError("retrospective annual rebuild cannot grant production authority")

    def specialist_spec(self) -> TimingSpecialistProgressiveRouteSpec:
        return TimingSpecialistProgressiveRouteSpec(
            reference_history_days=self.reference_history_days,
            reference_minimum_days=self.reference_minimum_days,
            crash_default_breadth_minimum=self.crash_default_breadth_minimum,
            crash_strict_breadth_minimum=self.crash_strict_breadth_minimum,
            paper_default_trend_days=self.paper_default_trend_days,
            paper_alternate_trend_days=self.paper_alternate_trend_days,
            paper_tail_quantile=self.paper_tail_quantile,
            paper_band_heat_minimum=self.paper_band_heat_minimum,
            paper_signed_path_efficiency_minimum=self.paper_signed_path_efficiency_minimum,
            paper_fast_band_change_minimum=self.paper_fast_band_change_minimum,
            ols_default_jump_minimum=self.ols_default_jump_minimum,
            ols_relaxed_jump_minimum=self.ols_relaxed_jump_minimum,
            ols_band_change_minimum=self.ols_band_change_minimum,
            ols_signed_path_efficiency_maximum=self.ols_signed_path_efficiency_maximum,
        )

    def residual_spec(self) -> TimingMarketFieldIIRSupplementSpec:
        return TimingMarketFieldIIRSupplementSpec(
            reference_history_days=self.residual_reference_history_days,
            reference_minimum_days=self.residual_reference_minimum_days,
            variance_ratio_scale_days=self.residual_variance_ratio_scale_days,
            variance_ratio_quantile=self.residual_variance_ratio_quantile,
            path_efficiency_scale_days=self.residual_path_efficiency_scale_days,
            path_efficiency_quantile=self.residual_path_efficiency_quantile,
            highpass_cutoff_days=self.residual_highpass_cutoff_days,
            highpass_power_heat_maximum=self.residual_highpass_power_heat_maximum,
        )

    def payload(self) -> dict[str, object]:
        values = asdict(self)
        # Preserve the semantic identity of snapshots frozen before this
        # optional route existed.  The extension enters the digest only when
        # it has behavioral authority.
        if self.ols_prior_20d_return_floor is None:
            values.pop("ols_prior_20d_return_floor")
        if self.use_progressive_paper_up:
            values.pop("use_progressive_paper_up")
        if self.use_progressive_ols_down:
            values.pop("use_progressive_ols_down")
        if self.residual_long_prior_return_minimum is None:
            values.pop("residual_long_prior_return_lookback_days")
            values.pop("residual_long_prior_return_minimum")
        if self.residual_long_recovery_return_minimum is None:
            values.pop("residual_long_recovery_return_lookback_days")
            values.pop("residual_long_recovery_return_minimum")
        if self.residual_long_highpass_power_heat_maximum is None:
            values.pop("residual_long_highpass_power_heat_maximum")
        return {"schema_id": SCHEMA_ID, **values}

    def semantic_digest(self) -> str:
        return canonical_digest(self.payload())


def common_root_spec() -> IsolatedAnnualPolicySpec:
    """Return the clean-room branch's only inherited strategy formula."""

    return IsolatedAnnualPolicySpec(candidate_id=COMMON_ROOT_POLICY_ID)


def gate_residual_long_lifecycles(
    residual_desired: pd.Series,
    strictly_prior_return: pd.Series | None,
    *,
    minimum: float | None,
    strictly_prior_recovery_return: pd.Series | None = None,
    recovery_minimum: float | None = None,
    strictly_prior_highpass_heat: pd.Series | None = None,
    highpass_heat_maximum: float | None = None,
) -> pd.DataFrame:
    """Accept or reject each positive residual lifecycle at its entry only.

    The primary long-background gate and optional short-horizon recovery
    release are an OR condition.  Both measurements are strictly prior, and
    the resulting decision is frozen for the complete positive lifecycle.
    """

    if (strictly_prior_return is None) != (minimum is None):
        raise ValueError("background return and minimum must be supplied together")
    if strictly_prior_return is not None and not residual_desired.index.equals(
        strictly_prior_return.index
    ):
        raise ValueError("residual target and prior return indexes must match")
    if (strictly_prior_recovery_return is None) != (recovery_minimum is None):
        raise ValueError("recovery return and recovery minimum must be supplied together")
    if strictly_prior_recovery_return is not None and not residual_desired.index.equals(
        strictly_prior_recovery_return.index
    ):
        raise ValueError("residual target and recovery return indexes must match")
    if (strictly_prior_highpass_heat is None) != (highpass_heat_maximum is None):
        raise ValueError("highpass heat and maximum must be supplied together")
    if strictly_prior_highpass_heat is not None and not residual_desired.index.equals(
        strictly_prior_highpass_heat.index
    ):
        raise ValueError("residual target and highpass heat indexes must match")
    if strictly_prior_return is None and strictly_prior_highpass_heat is None:
        raise ValueError("at least one causal entry condition is required")
    residual = pd.to_numeric(residual_desired, errors="raise").fillna(0.0).clip(-1.0, 1.0)
    entry_keep = pd.Series(True, index=residual.index, dtype=bool)
    if strictly_prior_return is not None and minimum is not None:
        entry_keep &= pd.to_numeric(strictly_prior_return, errors="coerce").ge(minimum)
    if strictly_prior_recovery_return is not None and recovery_minimum is not None:
        recovery_keep = pd.to_numeric(
            strictly_prior_recovery_return, errors="coerce"
        ).ge(recovery_minimum)
        background_keep = pd.to_numeric(
            cast(pd.Series, strictly_prior_return), errors="coerce"
        ).ge(cast(float, minimum))
        entry_keep = background_keep | recovery_keep
    if strictly_prior_highpass_heat is not None and highpass_heat_maximum is not None:
        entry_keep &= pd.to_numeric(
            strictly_prior_highpass_heat, errors="coerce"
        ).le(highpass_heat_maximum)
    route = gate_complete_lifecycle_by_entry_threshold(
        residual.gt(0.0),
        entry_keep.astype(float),
        1.0,
    )
    gated = residual.copy()
    rejected_long = residual.gt(0.0) & ~cast(pd.Series, route["gated_lifecycle"]).astype(bool)
    gated.loc[rejected_long] = 0.0
    return pd.DataFrame(
        {
            "policy_residual_desired_position": gated,
            "residual_long_entry_trigger": route["entry_trigger"],
            "residual_long_entry_accepted": route["entry_accepted"],
            "residual_long_lifecycle_accepted": route["gated_lifecycle"],
        },
        index=residual.index,
    )


def build_policy_positions(
    market15: pd.DataFrame,
    market60: pd.DataFrame,
    field_v2: pd.DataFrame,
    field_v4: pd.DataFrame,
    *,
    crash_rebound: pd.Series,
    rebound_breadth: pd.Series,
    cutoff: pd.Timestamp,
    policy: IsolatedAnnualPolicySpec,
) -> pd.DataFrame:
    """Build a complete causal position path from one isolated policy spec."""

    positions = build_three_bucket_iir_reference_v4(
        market15,
        market60,
        field_v2,
        field_v4,
        frozen_crash_rebound_executable=crash_rebound,
        rebound_breadth_by_completed_bar=rebound_breadth,
        allowed_end_exclusive=cutoff,
        account_spec=TimingThreeBucketIIRReferenceSpec(),
        residual_field_spec=policy.residual_spec(),
        specialist_spec=policy.specialist_spec(),
    ).copy()
    index = positions.index
    close = pd.Series(
        pd.to_numeric(market15["close"], errors="raise").to_numpy(float),
        index=index,
    )
    strictly_prior_20d_return = close.pct_change(20 * 16).shift(1)
    positions["ols_prior_20d_return"] = strictly_prior_20d_return
    residual_lookback_bars = policy.residual_long_prior_return_lookback_days * 16
    residual_prior_return = close.pct_change(residual_lookback_bars).shift(1)
    positions["residual_long_prior_return"] = residual_prior_return
    residual_recovery_bars = policy.residual_long_recovery_return_lookback_days * 16
    residual_recovery_return = close.pct_change(residual_recovery_bars).shift(1)
    positions["residual_long_recovery_return"] = residual_recovery_return
    field_eligible_index = pd.DatetimeIndex(field_v2["decision_eligible_date"]).normalize()
    if field_eligible_index.has_duplicates:
        raise ValueError("market-field decision-eligible dates must be unique")
    daily_highpass_heat = pd.Series(
        pd.to_numeric(
            field_v2["cumulative_highpass_power_heat_d4"], errors="raise"
        ).to_numpy(float),
        index=field_eligible_index,
    )
    residual_highpass_heat = pd.Series(
        daily_highpass_heat.reindex(pd.DatetimeIndex(index).normalize()).to_numpy(float),
        index=index,
    )
    positions["residual_long_highpass_power_heat"] = residual_highpass_heat
    residual_desired = cast(pd.Series, positions["dynamic_iir_desired_position"]).astype(float)
    positions["policy_residual_desired_position"] = residual_desired
    positions["residual_long_entry_accepted"] = pd.Series(False, index=index, dtype=bool)
    positions["residual_long_heat_entry_accepted"] = pd.Series(False, index=index, dtype=bool)
    if (
        policy.residual_long_prior_return_minimum is not None
        or policy.residual_long_highpass_power_heat_maximum is not None
    ):
        residual_route = gate_residual_long_lifecycles(
            residual_desired,
            (
                residual_prior_return
                if policy.residual_long_prior_return_minimum is not None
                else None
            ),
            minimum=policy.residual_long_prior_return_minimum,
            strictly_prior_recovery_return=(
                residual_recovery_return
                if policy.residual_long_recovery_return_minimum is not None
                else None
            ),
            recovery_minimum=policy.residual_long_recovery_return_minimum,
            strictly_prior_highpass_heat=(
                residual_highpass_heat
                if policy.residual_long_highpass_power_heat_maximum is not None
                else None
            ),
            highpass_heat_maximum=policy.residual_long_highpass_power_heat_maximum,
        )
        residual_desired = cast(
            pd.Series, residual_route["policy_residual_desired_position"]
        ).astype(float)
        positions["policy_residual_desired_position"] = residual_desired
        positions["residual_long_entry_accepted"] = residual_route[
            "residual_long_entry_accepted"
        ]
        positions["residual_long_heat_entry_accepted"] = residual_route[
            "residual_long_entry_accepted"
        ]
        positions["residual_long_prior_return_minimum"] = (
            policy.residual_long_prior_return_minimum
        )
        positions["residual_long_recovery_return_minimum"] = (
            policy.residual_long_recovery_return_minimum
        )
        positions["residual_long_highpass_power_heat_maximum"] = (
            policy.residual_long_highpass_power_heat_maximum
        )
    else:
        positions["residual_long_prior_return_minimum"] = pd.Series(np.nan, index=index)
        positions["residual_long_recovery_return_minimum"] = pd.Series(np.nan, index=index)
        positions["residual_long_highpass_power_heat_maximum"] = pd.Series(np.nan, index=index)
    paper_position = (
        cast(pd.Series, positions["paper_progressive_executable_position"]).astype(float)
        if policy.use_progressive_paper_up
        else cast(pd.Series, positions["v2_paper_s2_up_q925"]).astype(float)
    )
    ols_decision_active = (
        cast(pd.Series, positions["ols_progressive_decision_active"]).astype(bool)
        if policy.use_progressive_ols_down
        else cast(pd.Series, positions["v2_ols_down_gated"]).astype(bool)
    )
    ols_position = (
        cast(pd.Series, positions["ols_progressive_executable_position"]).astype(float)
        if policy.use_progressive_ols_down
        else pd.Series(
            np.where(ols_decision_active, -1.0, 0.0),
            index=index,
            dtype=float,
        )
    )
    if policy.ols_prior_20d_return_floor is not None:
        exhaustion_gate = gate_complete_lifecycle_by_entry_threshold(
            ols_decision_active,
            strictly_prior_20d_return,
            policy.ols_prior_20d_return_floor,
        )
        ols_position = enforce_true_t_plus_one(
            cast(pd.Series, exhaustion_gate["gated_lifecycle"]), side="down"
        ).astype(float)
        positions["ols_prior_20d_return_floor"] = policy.ols_prior_20d_return_floor
        positions["ols_exhaustion_entry_accepted"] = exhaustion_gate["entry_accepted"]
        positions["ols_progressive_executable_position"] = ols_position
    else:
        positions["ols_prior_20d_return_floor"] = pd.Series(np.nan, index=positions.index)
        positions["ols_exhaustion_entry_accepted"] = pd.Series(False, index=positions.index)
    positions["policy_paper_up_executable_position"] = paper_position
    positions["policy_ols_down_executable_position"] = ols_position
    if (
        policy.ols_prior_20d_return_floor is not None
        or policy.residual_long_prior_return_minimum is not None
        or policy.residual_long_highpass_power_heat_maximum is not None
        or not policy.use_progressive_paper_up
        or not policy.use_progressive_ols_down
    ):
        claims = compose_ordered_specialist_claims(
            residual_desired,
            {
                "crash_rebound": cast(pd.Series, positions["crash_rebound_progressive"]).astype(float),
                "paper_up": paper_position,
                "ols_down": ols_position,
            },
        )
        positions["crash_rebound_claim"] = claims["crash_rebound_claim"]
        positions["paper_up_claim"] = claims["paper_up_claim"]
        positions["ols_down_claim"] = claims["ols_down_claim"]
        positions["residual_iir_claim"] = claims["residual_claim"]
        positions["combo_desired_position"] = claims["combo_desired_position"]
        positions["combo_desired_owner"] = claims["combo_desired_owner"]
        positions["combo_t1_position"] = claims["combo_t1_position"]
        positions["combo_t1_owner"] = claims["combo_t1_owner"]
    positions["policy_id"] = policy.candidate_id
    positions["policy_digest"] = policy.semantic_digest()
    return positions


def build_policy_owner_counterfactual_positions(positions: pd.DataFrame) -> pd.DataFrame:
    """Reprice every isolated-branch owner against the unchanged V2 account."""

    required = {
        "v2_combo_t1_position",
        "dynamic_iir_desired_position",
        "policy_residual_desired_position",
        "v2_crash_rebound_gated",
        "v2_paper_s2_up_q925",
        "v2_ols_down_gated",
        "crash_rebound_progressive",
        "policy_paper_up_executable_position",
        "policy_ols_down_executable_position",
        "combo_t1_position",
    }
    missing = sorted(required.difference(positions.columns))
    if missing:
        raise KeyError(f"isolated owner counterfactual is missing columns: {missing}")
    index = positions.index
    base_residual = cast(pd.Series, positions["dynamic_iir_desired_position"]).astype(float)
    policy_residual = cast(pd.Series, positions["policy_residual_desired_position"]).astype(float)
    v2_specialists = {
        "crash_rebound": cast(pd.Series, positions["v2_crash_rebound_gated"]).astype(float),
        "paper_up": cast(pd.Series, positions["v2_paper_s2_up_q925"]).astype(float),
        "ols_down": pd.Series(
            np.where(cast(pd.Series, positions["v2_ols_down_gated"]).astype(bool), -1.0, 0.0),
            index=index,
            dtype=float,
        ),
    }
    policy_specialists = {
        "crash_rebound": cast(pd.Series, positions["crash_rebound_progressive"]).astype(float),
        "paper_up": cast(pd.Series, positions["policy_paper_up_executable_position"]).astype(float),
        "ols_down": cast(pd.Series, positions["policy_ols_down_executable_position"]).astype(float),
    }

    def compose(residual: pd.Series, specialists: dict[str, pd.Series]) -> pd.Series:
        return cast(
            pd.Series,
            compose_ordered_specialist_claims(residual, specialists)["combo_t1_position"],
        )

    baseline = compose(base_residual, v2_specialists)
    combined = compose(policy_residual, policy_specialists)
    if not baseline.equals(cast(pd.Series, positions["v2_combo_t1_position"])):
        raise RuntimeError("isolated counterfactual failed to reproduce V2")
    if not combined.equals(cast(pd.Series, positions["combo_t1_position"])):
        raise RuntimeError("isolated counterfactual failed to reproduce the complete policy")
    return pd.DataFrame(
        {
            "v2_reference": baseline,
            "crash_rebound_only": compose(
                base_residual, {**v2_specialists, "crash_rebound": policy_specialists["crash_rebound"]}
            ),
            "paper_up_only": compose(
                base_residual, {**v2_specialists, "paper_up": policy_specialists["paper_up"]}
            ),
            "ols_down_only": compose(
                base_residual, {**v2_specialists, "ols_down": policy_specialists["ols_down"]}
            ),
            "residual_route_only": compose(policy_residual, v2_specialists),
            "combined_policy": combined,
        },
        index=index,
    )


def annual_account_metrics(
    market15: pd.DataFrame,
    positions: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
) -> dict[str, object]:
    index = pd.DatetimeIndex(pd.to_datetime(market15["timestamp"], errors="raise"))
    opens = pd.Series(pd.to_numeric(market15["open"], errors="raise").to_numpy(float), index=index)
    strategy = aggregate_account_metrics(
        opens,
        cast(pd.Series, positions["combo_t1_position"]),
        start=start,
        end_exclusive=end_exclusive,
        isolate_end_boundary=True,
    )
    buy_hold = aggregate_account_metrics(
        opens,
        pd.Series(1.0, index=index),
        start=start,
        end_exclusive=end_exclusive,
        isolate_end_boundary=True,
    )
    strategy["excess_net_log_return_to_buy_hold"] = float(strategy["net_log_return"]) - float(
        buy_hold["net_log_return"]
    )
    return {"strategy": strategy, "buy_hold": buy_hold}


def build_trade_episode_ledger(
    market15: pd.DataFrame,
    positions: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
) -> pd.DataFrame:
    """Describe every completed signed-position episode in one year."""

    index = pd.DatetimeIndex(pd.to_datetime(market15["timestamp"], errors="raise"))
    opens = pd.Series(pd.to_numeric(market15["open"], errors="raise").to_numpy(float), index=index)
    position = pd.to_numeric(positions["combo_t1_position"], errors="raise").astype(float)
    rows: list[dict[str, object]] = []
    if index.empty:
        return pd.DataFrame()
    groups = position.ne(position.shift()).cumsum()
    for _, block in position.groupby(groups):
        sign = float(block.iloc[0])
        if sign == 0.0:
            continue
        entry = block.index[0]
        if entry < start or entry >= end_exclusive:
            continue
        final = block.index[-1]
        next_locations = index.get_indexer([final]) + 1
        exit_location = int(next_locations[0])
        if exit_location >= len(index) or index[exit_location] >= end_exclusive:
            continue
        exit_time = index[exit_location]
        path = np.log(opens.loc[block.index] / float(opens.loc[entry])) * sign
        gross = sign * float(np.log(opens.loc[exit_time] / opens.loc[entry]))
        cost = 0.0007
        executed_owners = positions.loc[block.index, "combo_t1_owner"].astype("string")
        owner = str(executed_owners.value_counts().index[0])
        rows.append(
            {
                "entry_time": entry,
                "exit_time": exit_time,
                "side": "long" if sign > 0 else "short",
                "owner": owner,
                "hold_15m_bars": int(len(block)),
                "gross_log_return": gross,
                "net_log_return": gross - cost,
                "maximum_favorable_excursion": float(path.max()),
                "maximum_adverse_excursion": float(path.min()),
                "profitable": bool(gross - cost > 0),
                "short_whipsaw": bool(len(block) <= 4 and gross - cost <= 0),
            }
        )
    return pd.DataFrame(rows)


def _candidate_event_windows(
    opens: pd.Series,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
) -> pd.DataFrame:
    local = opens.loc[(opens.index >= start) & (opens.index < end_exclusive)]
    rows: list[dict[str, object]] = []
    for horizon in (16, 32, 80, 160):
        forward = np.log(local.shift(-horizon) / local)
        for timestamp, value in forward.dropna().items():
            rows.append(
                {
                    "start_time": timestamp,
                    "end_time": local.index[local.index.get_loc(timestamp) + horizon],
                    "horizon_15m_bars": horizon,
                    "market_log_return": float(value),
                    "absolute_market_log_return": abs(float(value)),
                }
            )
    return pd.DataFrame(rows)


def build_directional_event_ledger(
    market15: pd.DataFrame,
    positions: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    events_per_side: int = 8,
) -> pd.DataFrame:
    """Build a de-duplicated hindsight opportunity ledger for attribution only."""

    index = pd.DatetimeIndex(pd.to_datetime(market15["timestamp"], errors="raise"))
    opens = pd.Series(pd.to_numeric(market15["open"], errors="raise").to_numpy(float), index=index)
    windows = _candidate_event_windows(opens, start=start, end_exclusive=end_exclusive)
    selected: list[pd.Series] = []
    for side in (1, -1):
        ranked = windows.loc[np.sign(windows["market_log_return"]).eq(side)].sort_values(
            "absolute_market_log_return", ascending=False
        )
        side_selected: list[pd.Series] = []
        for _, row in ranked.iterrows():
            overlaps = any(
                row["start_time"] < kept["end_time"] and kept["start_time"] < row["end_time"]
                for kept in side_selected
            )
            if overlaps:
                continue
            side_selected.append(row)
            if len(side_selected) >= events_per_side:
                break
        selected.extend(side_selected)
    account = signed_position_ledger(
        opens,
        pd.to_numeric(positions["combo_t1_position"], errors="raise").astype(float),
    )
    output: list[dict[str, object]] = []
    for ordinal, row in enumerate(
        sorted(selected, key=lambda item: cast(pd.Timestamp, item["start_time"])), start=1
    ):
        event_start = cast(pd.Timestamp, row["start_time"])
        event_end = cast(pd.Timestamp, row["end_time"])
        local = account.loc[(account.index >= event_start) & (account.index < event_end)]
        market_return = float(row["market_log_return"])
        direction = 1.0 if market_return > 0 else -1.0
        market_path = np.log(opens.loc[local.index].shift(-1) / opens.loc[local.index]).dropna()
        executed_owners = positions.loc[local.index, "combo_t1_owner"].astype("string")
        non_flat_owners = executed_owners.loc[executed_owners.ne("none")]
        dominant_owner = (
            str(non_flat_owners.value_counts().index[0]) if not non_flat_owners.empty else "none"
        )
        output.append(
            {
                "event_id": f"event_{ordinal:02d}",
                "start_time": event_start,
                "end_time": event_end,
                "direction": "up" if direction > 0 else "down",
                "horizon_15m_bars": int(row["horizon_15m_bars"]),
                "market_log_return": market_return,
                "path_efficiency": abs(market_return) / float(market_path.abs().sum())
                if float(market_path.abs().sum()) > 0
                else 0.0,
                "strategy_net_log_return": float(local["net_log_return"].sum()),
                "aligned_exposure_share": float(local["position"].eq(direction).mean()),
                "opposite_exposure_share": float(local["position"].eq(-direction).mean()),
                "flat_exposure_share": float(local["position"].eq(0.0).mean()),
                "dominant_owner": dominant_owner,
                "opportunity_label_uses_future": True,
                "runtime_feature_authority": False,
            }
        )
    return pd.DataFrame(output)


__all__ = [
    "COMMON_ROOT_POLICY_DIGEST",
    "COMMON_ROOT_POLICY_ID",
    "IsolatedAnnualPolicySpec",
    "SCHEMA_ID",
    "annual_account_metrics",
    "build_directional_event_ledger",
    "build_policy_positions",
    "build_policy_owner_counterfactual_positions",
    "build_trade_episode_ledger",
    "common_root_spec",
    "gate_residual_long_lifecycles",
]
