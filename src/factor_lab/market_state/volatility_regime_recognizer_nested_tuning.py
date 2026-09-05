# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportMissingTypeStubs=false
# pyright: reportUnknownVariableType=false, reportAttributeAccessIssue=false
# pyright: reportIndexIssue=false, reportCallIssue=false
"""Equal-budget parameter families for nested volatility-recognizer tuning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.volatility_regime_recognizer_battle import (
    INVALID_STATE,
    agreement_transition,
    apply_confirmation_hysteresis,
    bocpd_states,
    cusum_state_machine,
    filter_ordered_gaussian_hmm,
    fit_ordered_gaussian_hmm,
    quantile_states,
)

FAMILY_IDS: Final[tuple[str, ...]] = (
    "simple_quantile_v1",
    "simple_hysteresis_v1",
    "cusum_rv_v1",
    "bocpd_rv_v1",
    "gaussian_hmm_rv_v1",
    "bipower_hard_v1",
    "bipower_cusum_v1",
    "bipower_bocpd_v1",
    "bipower_hmm_v1",
    "bipower_hmm_bocpd_v1",
)
PROFILES_PER_FAMILY: Final = 12
MU1: Final = float(np.sqrt(2.0 / np.pi))


@dataclass(frozen=True, slots=True)
class ParameterProfile:
    family_id: str
    profile_id: str
    parameters: dict[str, float | int]
    complexity_units: int


def build_equal_budget_profiles() -> tuple[ParameterProfile, ...]:
    rows: list[ParameterProfile] = []

    def add(family: str, parameters: dict[str, float | int], complexity: int) -> None:
        index = sum(item.family_id == family for item in rows) + 1
        rows.append(ParameterProfile(family, f"{family}__p{index:02d}", parameters, complexity))

    for window in (8, 16, 32):
        for history in (256, 512):
            for low, high in ((0.25, 0.75), (1.0 / 3.0, 2.0 / 3.0)):
                add("simple_quantile_v1", {"window": window, "history": history, "low_q": low, "high_q": high}, 1)
    for confirmations in (1, 2, 3):
        for residence in (2, 4, 8, 16):
            add(
                "simple_hysteresis_v1",
                {
                    "window": 16,
                    "history": 512,
                    "low_q": 1.0 / 3.0,
                    "high_q": 2.0 / 3.0,
                    "confirmations": confirmations,
                    "residence": residence,
                },
                2,
            )
    for window in (8, 16, 32):
        for threshold in (2.0, 3.0, 4.0, 5.0):
            add("cusum_rv_v1", {"window": window, "allowance": 0.25, "threshold": threshold}, 3)
    for window in (8, 16, 32):
        for hazard in (32, 64, 128, 256):
            add("bocpd_rv_v1", {"window": window, "hazard": hazard, "max_run": min(512, 4 * hazard)}, 4)
    for window in (8, 16, 32):
        for fast_weight in (0.5, 0.7, 0.85, 1.0):
            add("gaussian_hmm_rv_v1", {"window": window, "fast_weight": fast_weight, "variance_floor": 0.05}, 5)
    for window in (8, 16, 32):
        for jump_q in (0.75, 0.85):
            for low, high in ((0.25, 0.75), (1.0 / 3.0, 2.0 / 3.0)):
                add("bipower_hard_v1", {"window": window, "history": 512, "jump_q": jump_q, "low_q": low, "high_q": high}, 3)
    for window in (8, 16, 32):
        for threshold in (2.0, 3.0, 4.0, 5.0):
            add("bipower_cusum_v1", {"window": window, "allowance": 0.25, "threshold": threshold, "jump_q": 0.8}, 5)
    for window in (8, 16, 32):
        for hazard in (32, 64, 128, 256):
            add("bipower_bocpd_v1", {"window": window, "hazard": hazard, "max_run": min(512, 4 * hazard), "jump_q": 0.8}, 6)
    for window in (8, 16, 32):
        for continuous_weight in (0.5, 0.7, 0.85, 1.0):
            add("bipower_hmm_v1", {"window": window, "continuous_weight": continuous_weight, "variance_floor": 0.05}, 7)
            add(
                "bipower_hmm_bocpd_v1",
                {"window": window, "continuous_weight": continuous_weight, "variance_floor": 0.05, "hazard": 4 * window},
                9,
            )
    counts = {family: sum(item.family_id == family for item in rows) for family in FAMILY_IDS}
    if counts != {family: PROFILES_PER_FAMILY for family in FAMILY_IDS}:
        raise ValidationError(f"equal-budget profile construction failed: {counts}")
    return tuple(rows)


class DynamicFeatureCache:
    """Cache causal rolling volatility and bipower features by physical window."""

    def __init__(self, panel: pd.DataFrame) -> None:
        self.panel: pd.DataFrame = panel
        self._window_cache: dict[int, pd.DataFrame] = {}
        self._quantile_cache: dict[tuple[int, str, int, float], np.ndarray] = {}

    def window(self, bars: int) -> pd.DataFrame:
        if bars in self._window_cache:
            return self._window_cache[bars]
        result = pd.DataFrame(index=self.panel.index)
        log_return = self.panel["log_return"].astype(float)
        segment = self.panel["segment_id"].astype(int)
        rv = pd.Series(np.nan, index=self.panel.index, dtype=float)
        slow_rv = pd.Series(np.nan, index=self.panel.index, dtype=float)
        bv = pd.Series(np.nan, index=self.panel.index, dtype=float)
        for _, locations in segment.groupby(segment, sort=False).groups.items():
            loc = np.asarray(list(locations), dtype=int)
            returns = log_return.iloc[loc]
            squared = returns.pow(2)
            rv.iloc[loc] = np.sqrt(squared.rolling(bars, min_periods=bars).sum()).to_numpy(float)
            slow_rv.iloc[loc] = np.sqrt(squared.rolling(4 * bars, min_periods=4 * bars).sum()).to_numpy(float)
            cross = returns.abs() * returns.abs().shift(1)
            bv.iloc[loc] = ((MU1**-2) * cross.rolling(bars, min_periods=bars).sum()).to_numpy(float)
        rv_var = rv.pow(2)
        continuous_var = np.minimum(np.maximum(bv, 0.0), np.maximum(rv_var, 0.0))
        jump_share = np.maximum(rv_var - continuous_var, 0.0) / np.maximum(rv_var, 1e-16)
        result["log_rv"] = np.log(np.maximum(rv, 1e-12))
        result["log_slow_rv"] = np.log(np.maximum(slow_rv, 1e-12))
        result["log_continuous"] = np.log(np.maximum(np.sqrt(continuous_var), 1e-12))
        result["jump_share"] = jump_share
        for column in ("log_rv", "log_slow_rv", "log_continuous", "jump_share"):
            values = result[column]
            history = values.rolling(512, min_periods=256)
            mean = history.mean().shift(1)
            std = history.std(ddof=0).shift(1).clip(lower=1e-12)
            result[f"{column}_z"] = (values - mean) / std
        self._window_cache[bars] = result
        return result

    def quantile(self, bars: int, column: str, history: int, q: float) -> np.ndarray:
        key = (bars, column, history, q)
        if key not in self._quantile_cache:
            values = self.window(bars)[column]
            self._quantile_cache[key] = values.rolling(history, min_periods=history // 2).quantile(q).shift(1).to_numpy(float)
        return self._quantile_cache[key]


def state_for_profile(
    panel: pd.DataFrame,
    cache: DynamicFeatureCache,
    profile: ParameterProfile,
    *,
    year: int,
    state_cache: dict[tuple[object, ...], np.ndarray] | None = None,
) -> np.ndarray:
    """Build one profile state using only rows before ``year`` for HMM fitting."""

    shared = state_cache if state_cache is not None else {}
    p = profile.parameters
    window = int(p["window"])
    features = cache.window(window)
    family = profile.family_id
    if family == "simple_quantile_v1":
        return _hard_state(cache, window, "log_rv", int(p["history"]), float(p["low_q"]), float(p["high_q"]))
    if family == "simple_hysteresis_v1":
        raw = _hard_state(cache, window, "log_rv", int(p["history"]), float(p["low_q"]), float(p["high_q"]))
        return apply_confirmation_hysteresis(raw, confirmations=int(p["confirmations"]), minimum_residence=int(p["residence"]))
    if family == "cusum_rv_v1":
        return cusum_state_machine(features["log_rv_z"].to_numpy(float), allowance=float(p["allowance"]), threshold=float(p["threshold"]))
    if family == "bocpd_rv_v1":
        return _bocpd(cache, window, "log_rv_z", int(p["hazard"]), int(p["max_run"]))
    if family == "gaussian_hmm_rv_v1":
        key = ("rv_hmm", year, window, float(p["fast_weight"]))
        if key not in shared:
            shared[key] = _hmm(
                panel, features, year, ("log_rv_z", "log_slow_rv_z"), np.array([float(p["fast_weight"]), 1.0 - float(p["fast_weight"])])
            )
        return shared[key]
    jump_alert = features["jump_share"].to_numpy(float) > cache.quantile(window, "jump_share", 512, float(p.get("jump_q", 0.8)))
    if family == "bipower_hard_v1":
        state = _hard_state(cache, window, "log_continuous", int(p["history"]), float(p["low_q"]), float(p["high_q"]))
        state[(state != INVALID_STATE) & jump_alert] = 2
        return state
    if family == "bipower_cusum_v1":
        return cusum_state_machine(
            features["log_continuous_z"].to_numpy(float),
            allowance=float(p["allowance"]),
            threshold=float(p["threshold"]),
            force_high=jump_alert,
        )
    if family == "bipower_bocpd_v1":
        return _bocpd(cache, window, "log_continuous_z", int(p["hazard"]), int(p["max_run"]), force_high=jump_alert)
    continuous_weight = float(p["continuous_weight"])
    hmm_key = ("bp_hmm", year, window, continuous_weight)
    if hmm_key not in shared:
        shared[hmm_key] = _hmm(
            panel, features, year, ("log_continuous_z", "jump_share_z"), np.array([continuous_weight, 1.0 - continuous_weight])
        )
    if family == "bipower_hmm_v1":
        return shared[hmm_key]
    if family == "bipower_hmm_bocpd_v1":
        bocpd = _bocpd(cache, window, "log_continuous_z", int(p["hazard"]), min(512, 4 * int(p["hazard"])), force_high=jump_alert)
        return agreement_transition(shared[hmm_key], bocpd)
    raise ValidationError(f"unsupported parameter family: {family}")


def _hard_state(cache: DynamicFeatureCache, window: int, column: str, history: int, low_q: float, high_q: float) -> np.ndarray:
    values = cache.window(window)[column].to_numpy(float)
    return quantile_states(values, cache.quantile(window, column, history, low_q), cache.quantile(window, column, history, high_q))


def _bocpd(
    cache: DynamicFeatureCache, window: int, column: str, hazard: int, max_run: int, *, force_high: np.ndarray | None = None
) -> np.ndarray:
    values = cache.window(window)[column].to_numpy(float)
    low = cache.quantile(window, column, 512, 1.0 / 3.0)
    high = cache.quantile(window, column, 512, 2.0 / 3.0)
    state, _ = bocpd_states(values, low, high, force_high=force_high, hazard_run_length=hazard, max_run_length=max_run)
    return state


def _hmm(panel: pd.DataFrame, features: pd.DataFrame, year: int, columns: tuple[str, str], weights: np.ndarray) -> np.ndarray:
    matrix = features[list(columns)].to_numpy(float)
    train_mask = panel["year"].to_numpy(int) < year
    current_mask = panel["year"].to_numpy(int) == year
    train = matrix[train_mask]
    train = train[np.isfinite(train).all(axis=1)]
    params = fit_ordered_gaussian_hmm(train, order_weights=weights, max_iterations=30, variance_floor=0.05)
    state = np.full(len(panel), INVALID_STATE, dtype=np.int8)
    current, _ = filter_ordered_gaussian_hmm(matrix[current_mask], params)
    state[current_mask] = current
    return state


def select_family_champions(material_metrics: pd.DataFrame) -> pd.DataFrame:
    annual = material_metrics.groupby(["family_id", "profile_id", "year"], as_index=False).agg(annual_score=("battle_score", "mean"))
    summary = annual.groupby(["family_id", "profile_id"], as_index=False).agg(
        mean_score=("annual_score", "mean"),
        worst_year_score=("annual_score", "min"),
        median_score=("annual_score", "median"),
        material_year_count=("year", "nunique"),
    )
    summary["family_best"] = summary.groupby("family_id")["mean_score"].transform("max")
    summary["within_one_point_plateau"] = summary["mean_score"] >= summary["family_best"] - 0.01
    summary = summary.sort_values(
        ["family_id", "mean_score", "worst_year_score", "profile_id"], ascending=[True, False, False, True], kind="mergesort"
    )
    return summary.groupby("family_id", as_index=False, sort=False).head(1).reset_index(drop=True)


__all__ = [
    "DynamicFeatureCache",
    "FAMILY_IDS",
    "PROFILES_PER_FAMILY",
    "ParameterProfile",
    "build_equal_budget_profiles",
    "select_family_champions",
    "state_for_profile",
]
