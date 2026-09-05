# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false
"""Layer 3b low/normal/high volatility states and historical battle metrics.

Continuous measurement is exposed through the Layer 2 adapter in
``timing_layer2_3_contracts``.  This module retains the historical combined
implementation for reproducibility; consumers must not treat its feature
builder as the public Layer 2 API.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Final, Literal, cast

import numpy as np
import pandas as pd
from scipy.special import gammaln

from factor_lab.core.errors import ValidationError

STATE_LOW: Final = 0
STATE_NORMAL: Final = 1
STATE_HIGH: Final = 2
INVALID_STATE: Final = -1

FAST_WINDOW: Final = 16
SLOW_WINDOW: Final = 64
THRESHOLD_HISTORY: Final = 512
TARGET_HORIZON: Final = 16
EVALUATION_OFFSETS: Final[tuple[int, ...]] = (0, 4, 8, 12)
MU1: Final = float(np.sqrt(2.0 / pi))
LOW_Q: Final = 1.0 / 3.0
HIGH_Q: Final = 2.0 / 3.0
JUMP_ALERT_Q: Final = 0.8

CandidateFamily = Literal["simple", "cusum", "bocpd", "hmm", "bipower"]
FOUR_LAYER_ROLE: Final[str] = "layer3b_strategy_ephemeral"
LIFECYCLE: Final[str] = (
    "replaceable_by_more_complete_layer2_measurement_not_a_long_term_foundation"
)


@dataclass(frozen=True, slots=True)
class RecognizerSpec:
    candidate_id: str
    family: CandidateFamily
    complexity_units: int
    uses_bipower: bool = False
    uses_hmm: bool = False
    uses_bocpd_transition: bool = False


CANDIDATE_SPECS: Final[tuple[RecognizerSpec, ...]] = (
    RecognizerSpec("simple_quantile_v1", "simple", 1),
    RecognizerSpec("simple_hysteresis_v1", "simple", 2),
    RecognizerSpec("cusum_rv_v1", "cusum", 3),
    RecognizerSpec("bocpd_rv_v1", "bocpd", 4),
    RecognizerSpec("gaussian_hmm_rv_v1", "hmm", 5, uses_hmm=True),
    RecognizerSpec("bipower_hard_v1", "bipower", 3, uses_bipower=True),
    RecognizerSpec("bipower_cusum_v1", "cusum", 5, uses_bipower=True),
    RecognizerSpec(
        "bipower_bocpd_v1", "bocpd", 6, uses_bipower=True, uses_bocpd_transition=True
    ),
    RecognizerSpec("bipower_hmm_v1", "hmm", 7, uses_bipower=True, uses_hmm=True),
    RecognizerSpec(
        "bipower_hmm_bocpd_v1",
        "hmm",
        9,
        uses_bipower=True,
        uses_hmm=True,
        uses_bocpd_transition=True,
    ),
)


def build_volatility_feature_panel(bars: pd.DataFrame) -> pd.DataFrame:
    """Create strictly causal recognizer features and an evaluation-only future target."""

    required = {"timestamp", "trading_day", "close"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise ValidationError(f"volatility recognizer bars missing columns: {missing}")
    frame = bars.copy().sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    timestamp = pd.DatetimeIndex(pd.to_datetime(frame["timestamp"], errors="raise"))
    if timestamp.duplicated().any() or not timestamp.is_monotonic_increasing:
        raise ValidationError("recognizer timestamps must be unique and ordered")
    close = cast(pd.Series, pd.to_numeric(frame["close"], errors="raise")).astype(float)
    if bool((close <= 0).any()):
        raise ValidationError("recognizer close must be positive")
    segment = (
        cast(pd.Series, frame["segment_id"]).astype(int)
        if "segment_id" in frame.columns
        else pd.Series(0, index=frame.index, dtype=int)
    )
    log_return = pd.Series(np.nan, index=frame.index, dtype=float)
    realised_variance = pd.Series(np.nan, index=frame.index, dtype=float)
    rv_slow = pd.Series(np.nan, index=frame.index, dtype=float)
    bipower_variation = pd.Series(np.nan, index=frame.index, dtype=float)
    future_variance = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, locations in segment.groupby(segment, sort=False).groups.items():
        loc = np.asarray(list(locations), dtype=int)
        segment_close = close.iloc[loc]
        segment_return = pd.Series(
            np.log(segment_close.to_numpy(float)), index=loc, dtype=float
        ).diff()
        segment_squared = segment_return.pow(2)
        log_return.iloc[loc] = segment_return.to_numpy(float)
        realised_variance.iloc[loc] = (
            segment_squared.rolling(FAST_WINDOW, min_periods=FAST_WINDOW)
            .sum()
            .to_numpy(float)
        )
        rv_slow.iloc[loc] = np.sqrt(
            segment_squared.rolling(SLOW_WINDOW, min_periods=SLOW_WINDOW)
            .sum()
            .to_numpy(float)
        )
        cross_abs = segment_return.abs() * segment_return.abs().shift(1)
        bipower_variation.iloc[loc] = (
            (MU1**-2)
            * cross_abs.rolling(FAST_WINDOW, min_periods=FAST_WINDOW).sum()
        ).to_numpy(float)
        future_variance.iloc[loc] = (
            segment_squared.rolling(TARGET_HORIZON, min_periods=TARGET_HORIZON)
            .sum()
            .shift(-TARGET_HORIZON)
            .to_numpy(float)
        )
    rv_fast = np.sqrt(realised_variance)
    continuous_variance = np.minimum(
        np.maximum(bipower_variation, 0.0), np.maximum(realised_variance, 0.0)
    )
    jump_variance = np.maximum(realised_variance - continuous_variance, 0.0)
    jump_share = jump_variance / np.maximum(realised_variance, 1e-16)

    log_rv_fast = np.log(np.maximum(rv_fast, 1e-12))
    log_rv_slow = np.log(np.maximum(rv_slow, 1e-12))
    log_continuous = np.log(np.maximum(np.sqrt(continuous_variance), 1e-12))
    result = pd.DataFrame(
        {
            "timestamp": timestamp,
            "trading_day": frame["trading_day"].astype(str),
            "year": pd.to_datetime(frame["trading_day"], errors="raise").dt.year,
            "segment_id": segment,
            "log_return": log_return,
            "rv_fast": rv_fast,
            "rv_slow": rv_slow,
            "log_rv_fast": log_rv_fast,
            "log_rv_slow": log_rv_slow,
            "continuous_variance": continuous_variance,
            "log_continuous_volatility": log_continuous,
            "jump_share": jump_share,
        }
    )
    _add_causal_reference_columns(result, "log_rv_fast", "rv")
    _add_causal_reference_columns(result, "log_rv_slow", "rv_slow")
    _add_causal_reference_columns(result, "log_continuous_volatility", "continuous")
    _add_causal_reference_columns(result, "jump_share", "jump")
    result["future_rv_16"] = np.sqrt(future_variance)
    return result


def _add_causal_reference_columns(frame: pd.DataFrame, source: str, prefix: str) -> None:
    values = cast(pd.Series, frame[source]).astype(float)
    history = values.rolling(THRESHOLD_HISTORY, min_periods=THRESHOLD_HISTORY // 2)
    mean = history.mean().shift(1)
    std = history.std(ddof=0).shift(1).clip(lower=1e-12)
    frame[f"{prefix}_z"] = (values - mean) / std
    frame[f"{prefix}_q_low"] = history.quantile(LOW_Q).shift(1)
    frame[f"{prefix}_q_high"] = history.quantile(HIGH_Q).shift(1)
    frame[f"{prefix}_q_jump"] = history.quantile(JUMP_ALERT_Q).shift(1)


def recognise_non_hmm_candidates(panel: pd.DataFrame) -> dict[str, np.ndarray]:
    """Run all candidate identities that need no prior-year HMM fitting."""

    rv_raw = quantile_states(
        panel["log_rv_fast"].to_numpy(float),
        panel["rv_q_low"].to_numpy(float),
        panel["rv_q_high"].to_numpy(float),
    )
    simple_hysteresis = apply_confirmation_hysteresis(
        rv_raw, confirmations=2, minimum_residence=4
    )
    cusum_rv = cusum_state_machine(panel["rv_z"].to_numpy(float))
    bocpd_rv_state, bocpd_rv_cp = bocpd_states(
        panel["rv_z"].to_numpy(float),
        panel["rv_z"].rolling(THRESHOLD_HISTORY, min_periods=256).quantile(LOW_Q).shift(1).to_numpy(float),
        panel["rv_z"].rolling(THRESHOLD_HISTORY, min_periods=256).quantile(HIGH_Q).shift(1).to_numpy(float),
    )
    bp_raw = bipower_raw_states(panel)
    bp_cusum = cusum_state_machine(
        panel["continuous_z"].to_numpy(float),
        force_high=_jump_alert(panel),
    )
    bp_bocpd_state, bp_bocpd_cp = bocpd_states(
        panel["continuous_z"].to_numpy(float),
        panel["continuous_z"]
        .rolling(THRESHOLD_HISTORY, min_periods=256)
        .quantile(LOW_Q)
        .shift(1)
        .to_numpy(float),
        panel["continuous_z"]
        .rolling(THRESHOLD_HISTORY, min_periods=256)
        .quantile(HIGH_Q)
        .shift(1)
        .to_numpy(float),
        force_high=_jump_alert(panel),
    )
    return {
        "simple_quantile_v1": rv_raw,
        "simple_hysteresis_v1": simple_hysteresis,
        "cusum_rv_v1": cusum_rv,
        "bocpd_rv_v1": bocpd_rv_state,
        "bipower_hard_v1": bp_raw,
        "bipower_cusum_v1": bp_cusum,
        "bipower_bocpd_v1": bp_bocpd_state,
        "_bocpd_rv_cp": bocpd_rv_cp,
        "_bipower_bocpd_cp": bp_bocpd_cp,
    }


def quantile_states(values: np.ndarray, low: np.ndarray, high: np.ndarray) -> np.ndarray:
    state = np.full(len(values), INVALID_STATE, dtype=np.int8)
    valid = np.isfinite(values) & np.isfinite(low) & np.isfinite(high) & (high > low)
    state[valid] = STATE_NORMAL
    state[valid & (values < low)] = STATE_LOW
    state[valid & (values > high)] = STATE_HIGH
    return state


def apply_confirmation_hysteresis(
    raw_state: np.ndarray,
    *,
    confirmations: int,
    minimum_residence: int,
) -> np.ndarray:
    output = np.full(len(raw_state), INVALID_STATE, dtype=np.int8)
    current = STATE_NORMAL
    candidate = STATE_NORMAL
    candidate_count = 0
    residence = minimum_residence
    initialized = False
    for index, desired in enumerate(raw_state):
        if desired == INVALID_STATE:
            continue
        if not initialized:
            current = int(desired)
            initialized = True
        if desired == current:
            candidate = current
            candidate_count = 0
        else:
            if desired == candidate:
                candidate_count += 1
            else:
                candidate = int(desired)
                candidate_count = 1
            if residence >= minimum_residence and candidate_count >= confirmations:
                current = candidate
                residence = 0
                candidate_count = 0
        output[index] = current
        residence += 1
    return output


def cusum_state_machine(
    zscore: np.ndarray,
    *,
    allowance: float = 0.25,
    threshold: float = 3.0,
    force_high: np.ndarray | None = None,
) -> np.ndarray:
    """Three-state state-dependent Page-style cumulative deviation machine."""

    output = np.full(len(zscore), INVALID_STATE, dtype=np.int8)
    current = STATE_NORMAL
    positive = 0.0
    negative = 0.0
    for index, value in enumerate(zscore):
        if not np.isfinite(value):
            continue
        positive = max(0.0, positive + float(value) - allowance)
        negative = min(0.0, negative + float(value) + allowance)
        forced = force_high is not None and bool(force_high[index])
        if forced:
            current = STATE_HIGH
            positive = 0.0
            negative = 0.0
        elif current == STATE_NORMAL:
            if positive >= threshold:
                current = STATE_HIGH
                positive = negative = 0.0
            elif negative <= -threshold:
                current = STATE_LOW
                positive = negative = 0.0
        elif current == STATE_HIGH and negative <= -threshold:
            current = STATE_NORMAL
            positive = negative = 0.0
        elif current == STATE_LOW and positive >= threshold:
            current = STATE_NORMAL
            positive = negative = 0.0
        output[index] = current
    return output


def _jump_alert(panel: pd.DataFrame) -> np.ndarray:
    jump = panel["jump_share"].to_numpy(float)
    threshold = panel["jump_q_jump"].to_numpy(float)
    return np.isfinite(jump) & np.isfinite(threshold) & (jump > threshold)


def bipower_raw_states(panel: pd.DataFrame) -> np.ndarray:
    state = quantile_states(
        panel["log_continuous_volatility"].to_numpy(float),
        panel["continuous_q_low"].to_numpy(float),
        panel["continuous_q_high"].to_numpy(float),
    )
    alert = _jump_alert(panel)
    state[(state != INVALID_STATE) & alert] = STATE_HIGH
    return state


def bocpd_states(
    values: np.ndarray,
    low_threshold: np.ndarray,
    high_threshold: np.ndarray,
    *,
    force_high: np.ndarray | None = None,
    hazard_run_length: int = 64,
    max_run_length: int = 256,
) -> tuple[np.ndarray, np.ndarray]:
    """Run a bounded Gaussian BOCPD and classify its posterior segment mean."""

    state = np.full(len(values), INVALID_STATE, dtype=np.int8)
    cp_probability = np.full(len(values), np.nan, dtype=float)
    hazard = 1.0 / float(hazard_run_length)
    run_prob = np.array([1.0], dtype=float)
    mu = np.array([0.0], dtype=float)
    kappa = np.array([1.0], dtype=float)
    alpha = np.array([2.0], dtype=float)
    beta = np.array([1.0], dtype=float)
    for index, value in enumerate(values):
        if not np.isfinite(value):
            run_prob = np.array([1.0], dtype=float)
            mu = np.array([0.0], dtype=float)
            kappa = np.array([1.0], dtype=float)
            alpha = np.array([2.0], dtype=float)
            beta = np.array([1.0], dtype=float)
            continue
        log_pred = _student_t_log_predictive(float(value), mu, kappa, alpha, beta)
        pred = np.exp(log_pred - float(np.max(log_pred)))
        growth = run_prob * (1.0 - hazard) * pred
        change = float(np.sum(run_prob * hazard * pred))
        new_prob = np.concatenate(([change], growth))
        if len(new_prob) > max_run_length + 1:
            new_prob = new_prob[: max_run_length + 1]
        total = float(new_prob.sum())
        new_prob = new_prob / max(total, 1e-300)

        prior_mu = np.array([0.0])
        prior_kappa = np.array([1.0])
        prior_alpha = np.array([2.0])
        prior_beta = np.array([1.0])
        old_mu = mu[: len(new_prob) - 1]
        old_kappa = kappa[: len(new_prob) - 1]
        old_alpha = alpha[: len(new_prob) - 1]
        old_beta = beta[: len(new_prob) - 1]
        upd_mu, upd_kappa, upd_alpha, upd_beta = _nig_update(
            float(value), old_mu, old_kappa, old_alpha, old_beta
        )
        first_mu, first_kappa, first_alpha, first_beta = _nig_update(
            float(value), prior_mu, prior_kappa, prior_alpha, prior_beta
        )
        mu = np.concatenate((first_mu, upd_mu))[: len(new_prob)]
        kappa = np.concatenate((first_kappa, upd_kappa))[: len(new_prob)]
        alpha = np.concatenate((first_alpha, upd_alpha))[: len(new_prob)]
        beta = np.concatenate((first_beta, upd_beta))[: len(new_prob)]
        run_prob = new_prob
        posterior_mean = float(np.sum(run_prob * mu))
        cp_probability[index] = float(run_prob[0])
        if not np.isfinite(low_threshold[index]) or not np.isfinite(high_threshold[index]):
            continue
        chosen = STATE_NORMAL
        if posterior_mean < low_threshold[index]:
            chosen = STATE_LOW
        elif posterior_mean > high_threshold[index]:
            chosen = STATE_HIGH
        if force_high is not None and bool(force_high[index]):
            chosen = STATE_HIGH
        state[index] = chosen
    return state, cp_probability


def _student_t_log_predictive(
    value: float,
    mu: np.ndarray,
    kappa: np.ndarray,
    alpha: np.ndarray,
    beta: np.ndarray,
) -> np.ndarray:
    degrees = 2.0 * alpha
    scale2 = beta * (kappa + 1.0) / np.maximum(alpha * kappa, 1e-12)
    standardized = np.square(value - mu) / np.maximum(degrees * scale2, 1e-12)
    return (
        gammaln((degrees + 1.0) / 2.0)
        - gammaln(degrees / 2.0)
        - 0.5 * np.log(np.maximum(degrees * pi * scale2, 1e-12))
        - ((degrees + 1.0) / 2.0) * np.log1p(standardized)
    )


def _nig_update(
    value: float,
    mu: np.ndarray,
    kappa: np.ndarray,
    alpha: np.ndarray,
    beta: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    next_kappa = kappa + 1.0
    next_mu = (kappa * mu + value) / next_kappa
    next_alpha = alpha + 0.5
    next_beta = beta + 0.5 * kappa * np.square(value - mu) / next_kappa
    return next_mu, next_kappa, next_alpha, next_beta


@dataclass(frozen=True, slots=True)
class HmmParameters:
    means: np.ndarray
    variances: np.ndarray
    transition: np.ndarray
    initial: np.ndarray
    order_weights: np.ndarray


def fit_ordered_gaussian_hmm(
    features: np.ndarray,
    *,
    order_weights: np.ndarray,
    max_iterations: int = 100,
    variance_floor: float = 0.05,
) -> HmmParameters:
    """Fit a deterministic diagonal Gaussian HMM and order states by risk score."""

    x = np.asarray(features, dtype=float)
    if x.ndim != 2 or x.shape[0] < 256 or x.shape[1] != len(order_weights):
        raise ValidationError("HMM training features are insufficient")
    if not np.isfinite(x).all():
        raise ValidationError("HMM training features must be finite")
    risk = x @ order_weights
    groups = np.array_split(np.argsort(risk, kind="stable"), 3)
    means = np.vstack([x[group].mean(axis=0) for group in groups])
    variances = np.vstack(
        [np.maximum(x[group].var(axis=0), variance_floor) for group in groups]
    )
    transition = np.full((3, 3), 0.075, dtype=float)
    np.fill_diagonal(transition, 0.85)
    initial = np.full(3, 1.0 / 3.0, dtype=float)
    previous = -np.inf
    for _ in range(max_iterations):
        emission = _log_diagonal_gaussian(x, means, variances)
        filtered, scales = _hmm_forward(emission, initial, transition)
        smoothed, xi = _hmm_backward(filtered, scales, emission, transition)
        weights = np.maximum(smoothed.sum(axis=0), 1e-12)
        means = (smoothed.T @ x) / weights[:, None]
        variances = np.vstack(
            [
                np.maximum(
                    (smoothed[:, state, None] * np.square(x - means[state])).sum(axis=0)
                    / weights[state],
                    variance_floor,
                )
                for state in range(3)
            ]
        )
        counts = xi.sum(axis=0) + 0.05 + np.eye(3) * 0.5
        transition = counts / counts.sum(axis=1, keepdims=True)
        initial = np.maximum(smoothed[0], 1e-12)
        initial /= initial.sum()
        likelihood = float(scales.sum())
        if np.isfinite(previous) and abs(likelihood - previous) <= 1e-6:
            break
        previous = likelihood
    semantic_order = np.argsort(means @ order_weights, kind="stable")
    return HmmParameters(
        means=means[semantic_order],
        variances=variances[semantic_order],
        transition=transition[np.ix_(semantic_order, semantic_order)],
        initial=initial[semantic_order],
        order_weights=np.asarray(order_weights, dtype=float),
    )


def filter_ordered_gaussian_hmm(
    features: np.ndarray,
    parameters: HmmParameters,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(features, dtype=float)
    probabilities = np.full((len(x), 3), np.nan, dtype=float)
    state = np.full(len(x), INVALID_STATE, dtype=np.int8)
    current = parameters.initial.copy()
    for index, row in enumerate(x):
        if not np.isfinite(row).all():
            current = parameters.initial.copy()
            continue
        log_emission = _log_diagonal_gaussian(
            row[None, :], parameters.means, parameters.variances
        )[0]
        predicted = current @ parameters.transition
        log_joint = np.log(np.maximum(predicted, 1e-300)) + log_emission
        log_joint -= _logsumexp(log_joint)
        current = np.exp(log_joint)
        probabilities[index] = current
        state[index] = int(np.argmax(current))
    return state, probabilities


def _log_diagonal_gaussian(
    x: np.ndarray, means: np.ndarray, variances: np.ndarray
) -> np.ndarray:
    return np.column_stack(
        [
            -0.5
            * (
                np.log(2.0 * pi * variances[state]).sum()
                + (np.square(x - means[state]) / variances[state]).sum(axis=1)
            )
            for state in range(3)
        ]
    )


def _hmm_forward(
    emission: np.ndarray, initial: np.ndarray, transition: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    rows = len(emission)
    filtered = np.empty((rows, 3), dtype=float)
    scales = np.empty(rows, dtype=float)
    joint = np.log(np.maximum(initial, 1e-300)) + emission[0]
    scales[0] = _logsumexp(joint)
    filtered[0] = joint - scales[0]
    log_transition = np.log(np.maximum(transition, 1e-300))
    for row in range(1, rows):
        predicted = np.array(
            [_logsumexp(filtered[row - 1] + log_transition[:, state]) for state in range(3)]
        )
        joint = predicted + emission[row]
        scales[row] = _logsumexp(joint)
        filtered[row] = joint - scales[row]
    return filtered, scales


def _hmm_backward(
    filtered: np.ndarray,
    scales: np.ndarray,
    emission: np.ndarray,
    transition: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    rows = len(filtered)
    log_transition = np.log(np.maximum(transition, 1e-300))
    beta = np.zeros_like(filtered)
    xi = np.empty((rows - 1, 3, 3), dtype=float)
    for row in range(rows - 2, -1, -1):
        for state in range(3):
            beta[row, state] = (
                _logsumexp(log_transition[state] + emission[row + 1] + beta[row + 1])
                - scales[row + 1]
            )
        log_xi = (
            filtered[row, :, None]
            + log_transition
            + emission[row + 1, None, :]
            + beta[row + 1, None, :]
        )
        log_xi -= _logsumexp(log_xi.ravel())
        xi[row] = np.exp(log_xi)
    gamma = filtered + beta
    gamma -= np.apply_along_axis(_logsumexp, 1, gamma)[:, None]
    return np.exp(gamma), xi


def _logsumexp(values: np.ndarray) -> float:
    maximum = float(np.max(values))
    return maximum + float(np.log(np.exp(values - maximum).sum()))


def agreement_transition(hmm_state: np.ndarray, bocpd_state: np.ndarray) -> np.ndarray:
    """Change state only when HMM and BOCPD agree; otherwise retain the prior state."""

    output = np.full(len(hmm_state), INVALID_STATE, dtype=np.int8)
    current = STATE_NORMAL
    initialized = False
    for index, (hmm_value, bocpd_value) in enumerate(zip(hmm_state, bocpd_state, strict=True)):
        if hmm_value == INVALID_STATE or bocpd_value == INVALID_STATE:
            continue
        if not initialized:
            current = int(hmm_value)
            initialized = True
        elif hmm_value == bocpd_value:
            current = int(hmm_value)
        output[index] = current
    return output


def evaluate_candidate_year(
    panel: pd.DataFrame,
    state: np.ndarray,
    *,
    candidate_id: str,
    year: int,
    complexity_units: int,
    partition: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    year_mask = panel["year"].to_numpy(int) == year
    year_locations = np.flatnonzero(year_mask)
    for offset in EVALUATION_OFFSETS:
        selected = year_locations[offset::TARGET_HORIZON]
        target = panel["future_rv_16"].to_numpy(float)[selected]
        predicted = state[selected]
        valid = np.isfinite(target) & (predicted != INVALID_STATE)
        target = target[valid]
        predicted = predicted[valid]
        if len(target) < 60:
            raise ValidationError(f"insufficient evaluation anchors for {candidate_id} {year} offset {offset}")
        q_low, q_high = np.quantile(target, [LOW_Q, HIGH_Q])
        actual = np.full(len(target), STATE_NORMAL, dtype=np.int8)
        actual[target < q_low] = STATE_LOW
        actual[target > q_high] = STATE_HIGH
        class_f1 = [_f1(actual == value, predicted == value) for value in range(3)]
        macro_f1 = float(np.mean(class_f1))
        tail_f1 = float(np.mean([class_f1[STATE_LOW], class_f1[STATE_HIGH]]))
        transition_f1 = _f1(actual[1:] != actual[:-1], predicted[1:] != predicted[:-1])
        spearman = float(pd.Series(predicted).corr(pd.Series(target), method="spearman"))
        occupancy = [float(np.mean(predicted == value)) for value in range(3)]
        minimum_occupancy = float(min(occupancy))
        conditional = [
            float(np.mean(target[predicted == value])) if np.any(predicted == value) else np.nan
            for value in range(3)
        ]
        monotonic = bool(
            np.isfinite(conditional).all()
            and conditional[STATE_LOW] < conditional[STATE_NORMAL] < conditional[STATE_HIGH]
        )
        base_score = (
            0.35 * macro_f1
            + 0.25 * ((spearman + 1.0) / 2.0)
            + 0.25 * tail_f1
            + 0.15 * transition_f1
            - 0.005 * float(complexity_units - 1)
        )
        score = base_score
        if minimum_occupancy < 0.1:
            score -= 0.1
        if not monotonic:
            score -= 0.1
        rows.append(
            {
                "partition": partition,
                "candidate_id": candidate_id,
                "year": year,
                "offset": offset,
                "anchor_count": len(target),
                "future_volatility_spearman": spearman,
                "macro_f1": macro_f1,
                "low_f1": class_f1[STATE_LOW],
                "normal_f1": class_f1[STATE_NORMAL],
                "high_f1": class_f1[STATE_HIGH],
                "low_high_tail_f1": tail_f1,
                "transition_f1": transition_f1,
                "low_occupancy": occupancy[STATE_LOW],
                "normal_occupancy": occupancy[STATE_NORMAL],
                "high_occupancy": occupancy[STATE_HIGH],
                "minimum_state_occupancy": minimum_occupancy,
                "state_order_monotonic": monotonic,
                "low_mean_future_rv": conditional[STATE_LOW],
                "normal_mean_future_rv": conditional[STATE_NORMAL],
                "high_mean_future_rv": conditional[STATE_HIGH],
                "transitions_per_1000_bars": float(np.mean(predicted[1:] != predicted[:-1]) * 1000.0),
                "complexity_units": complexity_units,
                "battle_score": float(np.clip(score, 0.0, 1.0)),
            }
        )
    return pd.DataFrame(rows)


def _f1(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual_bool = np.asarray(actual, dtype=bool)
    predicted_bool = np.asarray(predicted, dtype=bool)
    true_positive = int(np.sum(actual_bool & predicted_bool))
    false_positive = int(np.sum(~actual_bool & predicted_bool))
    false_negative = int(np.sum(actual_bool & ~predicted_bool))
    denominator = 2 * true_positive + false_positive + false_negative
    return 0.0 if denominator == 0 else float(2 * true_positive / denominator)


def candidate_spec(candidate_id: str) -> RecognizerSpec:
    for item in CANDIDATE_SPECS:
        if item.candidate_id == candidate_id:
            return item
    raise ValidationError(f"unknown recognizer candidate: {candidate_id}")


__all__ = [
    "CANDIDATE_SPECS",
    "EVALUATION_OFFSETS",
    "FOUR_LAYER_ROLE",
    "HmmParameters",
    "LIFECYCLE",
    "RecognizerSpec",
    "agreement_transition",
    "apply_confirmation_hysteresis",
    "bipower_raw_states",
    "bocpd_states",
    "build_volatility_feature_panel",
    "candidate_spec",
    "cusum_state_machine",
    "evaluate_candidate_year",
    "filter_ordered_gaussian_hmm",
    "fit_ordered_gaussian_hmm",
    "quantile_states",
    "recognise_non_hmm_candidates",
]
