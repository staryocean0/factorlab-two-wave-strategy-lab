"""v0.6.17 session-aware structural bounds for fine concentration.

The bound API consumes native OHLC plus authoritative DataHub support topology
(counts / membership metadata only). Fine prices, oracle profiles, counterpart
morphology, direction and outcomes are deliberately outside this API.
"""
from __future__ import annotations

import itertools
import math
from typing import Mapping, Sequence

import numpy as np

from .fine_concentration_identifiability_v0615 import _simplex_profile_bounds

SCHEMA = "two_wave_session_aware_information_set_bounds@0.6.17"
EXPECTED_SYMBOL = "000852.SH"
EXPECTED_SOURCE_KIND = "market_index_transaction_derived_1m"
EXPECTED_DATASET_VERSION = (
    "bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_"
    "factorlab_unified_missing_day_repaired_v8_20260824"
)
EXPECTED_DATE_RANGE = ("2015-01-05", "2020-12-31")
EXPECTED_SOURCE_ROWS = 349_923


def validate_source_identity(identity: Mapping[str, object]) -> None:
    """Fail closed unless the support surface matches the accepted DataHub lineage."""
    expected = {
        "symbol": EXPECTED_SYMBOL,
        "source_kind": EXPECTED_SOURCE_KIND,
        "dataset_version": EXPECTED_DATASET_VERSION,
        "source_rows": EXPECTED_SOURCE_ROWS,
    }
    for key, value in expected.items():
        if identity.get(key) != value:
            raise ValueError(f"source identity mismatch for {key}")
    date_range = identity.get("date_range")
    normalized_range = tuple(date_range) if isinstance(date_range, (list, tuple)) else None
    if normalized_range != EXPECTED_DATE_RANGE:
        raise ValueError("source identity mismatch for date_range")
    if int(identity.get("future_2021_plus_rows_loaded", -1)) != 0:
        raise ValueError("2021+ source rows are not allowed")


def _ordered_unique_timestamps(values: Sequence[str], *, field: str) -> tuple[str, ...]:
    out = tuple(str(x) for x in values)
    if len(set(out)) != len(out):
        raise ValueError(f"duplicate source timestamp in {field}")
    if out != tuple(sorted(out)):
        raise ValueError(f"source timestamps must be ordered in {field}")
    return out


def validate_transition_topology(
    support_source_timestamps: Sequence[str],
    gap_source_timestamps: Sequence[str],
    source_timestamps_between_endpoints: Sequence[str] | None = None,
) -> dict:
    """Validate one price-blind support/gap partition and return its class.

    When ``source_timestamps_between_endpoints`` is supplied, support + gap must
    be an exact partition of that authoritative source-row universe.  This is
    the protocol-conformance guard that fails closed on a silently unclassified
    source row (or an unexpected source row invented by the topology builder).
    It consumes timestamps only; no source prices are accepted.
    """
    support = _ordered_unique_timestamps(
        support_source_timestamps, field="support_source_timestamps"
    )
    gap = _ordered_unique_timestamps(
        gap_source_timestamps, field="gap_source_timestamps"
    )
    if not support:
        raise ValueError("every emitted native bar requires non-empty support")
    if set(support).intersection(gap):
        raise ValueError("support and gap timestamps must be disjoint")

    if source_timestamps_between_endpoints is not None:
        expected = _ordered_unique_timestamps(
            source_timestamps_between_endpoints,
            field="source_timestamps_between_endpoints",
        )
        classified = set(support).union(gap)
        expected_set = set(expected)
        if classified != expected_set:
            missing = tuple(sorted(expected_set - classified))
            unexpected = tuple(sorted(classified - expected_set))
            raise ValueError(
                "support/gap topology is not an exact source-row partition: "
                f"missing={missing!r} unexpected={unexpected!r}"
            )

    return {
        "support_source_count": len(support),
        "gap_source_count": len(gap),
        "transition_class": (
            "contains_unenveloped_source_gap" if gap else "fully_enveloped_transition"
        ),
    }


def bar_tv_upper_variable(
    prev_close: float,
    low: float,
    high: float,
    close: float,
    support_source_count: int,
) -> float:
    """Exact covered-transition TV maximum for a variable number of fine steps."""
    c0, lo, hi, c1 = map(float, (prev_close, low, high, close))
    m = int(support_source_count)
    if not all(math.isfinite(x) for x in (c0, lo, hi, c1)):
        raise ValueError("finite prices required")
    if m < 1:
        raise ValueError("support_source_count must be >= 1")
    if hi < lo or c1 < lo or c1 > hi:
        raise ValueError("valid native bar envelope required")
    if m == 1:
        return float(abs(c1 - c0))

    best = 0.0
    for hidden in itertools.product((lo, hi), repeat=m - 1):
        path = (c0,) + hidden + (c1,)
        tv = sum(abs(b - a) for a, b in zip(path, path[1:]))
        best = max(best, tv)
    return float(best)


def covered_transition_bounds(
    prev_close: float,
    low: float,
    high: float,
    close: float,
    support_source_count: int,
) -> dict:
    """Return TV / maximum-step outer bounds for one fully enveloped transition."""
    c0, lo, hi, c1 = map(float, (prev_close, low, high, close))
    m = int(support_source_count)
    if m < 1:
        raise ValueError("support_source_count must be >= 1")
    if hi < lo or c1 < lo or c1 > hi:
        raise ValueError("valid native bar envelope required")
    d = abs(c1 - c0)
    if m == 1:
        tv_high = d
        m_high = d
    else:
        tv_high = bar_tv_upper_variable(c0, lo, hi, c1, m)
        m_high = max(
            abs(lo - c0),
            abs(hi - c0),
            hi - lo,
            abs(lo - c1),
            abs(hi - c1),
        )
    return {
        "support_source_count": m,
        "tv_low": float(d),
        "tv_high": float(tv_high),
        "m_low": float(d / m),
        "m_high": float(m_high),
    }


def _full_simplex_profile_bounds(n: int) -> dict:
    if n < 1:
        raise ValueError("positive fine step count required")
    cap = float(math.log(n))
    return {
        "c_inf_low": 0.0,
        "c_inf_high": cap,
        "c_1_low": 0.0,
        "c_1_high": cap,
        "c_2_low": 0.0,
        "c_2_high": cap,
    }


def _profile_bounds(n: int, j_low: float, j_high: float) -> dict:
    if n == 1:
        return _full_simplex_profile_bounds(1)
    return _simplex_profile_bounds(n, j_low, j_high)


def session_aware_concentration_bounds(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    support_source_counts: Sequence[int],
    gap_source_counts: Sequence[int],
) -> dict:
    """Return session-aware outer concentration bounds for one closed native leg.

    OHLC arrays include the published start anchor through end anchor. Support
    and gap counts correspond to transitions into rows 1..end. Counts must come
    from an already validated authoritative support-topology stage.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    if any(x.ndim != 1 for x in (h, l, c)):
        raise ValueError("one-dimensional OHLC arrays required")
    if not (len(h) == len(l) == len(c)) or len(c) < 2:
        raise ValueError("aligned OHLC arrays with at least two rows required")
    if not (np.isfinite(h).all() and np.isfinite(l).all() and np.isfinite(c).all()):
        raise ValueError("finite OHLC required")

    support = tuple(int(x) for x in support_source_counts)
    gaps = tuple(int(x) for x in gap_source_counts)
    b = len(c) - 1
    if len(support) != b or len(gaps) != b:
        raise ValueError("one support/gap count per native transition required")
    if any(m < 1 for m in support):
        raise ValueError("every emitted native bar requires positive source support")
    if any(g < 0 for g in gaps):
        raise ValueError("gap source counts must be nonnegative")

    n = int(sum(support) + sum(gaps))
    if n < 1:
        raise ValueError("positive fine step count required")
    gap_transition_count = sum(g > 0 for g in gaps)

    # A discarded source row has no authoritative neighboring native OHLC
    # envelope. Preserve the leg and use only universal probability-simplex
    # concentration bounds rather than inventing a price envelope.
    if gap_transition_count:
        prof = _full_simplex_profile_bounds(n)
        return {
            "schema": SCHEMA,
            "defined": True,
            "reason": None,
            "bound_class": "structural_gap_universal_bound",
            "native_transition_count": b,
            "fine_step_count": n,
            "support_source_count_total": int(sum(support)),
            "gap_source_count_total": int(sum(gaps)),
            "gap_transition_count": int(gap_transition_count),
            "j_low": float(1.0 / n),
            "j_high": 1.0,
            **prof,
            "conditional_on_positive_total_variation": True,
            "future_outcome_used": False,
            "trade_authority": False,
        }

    tv_low = 0.0
    tv_high = 0.0
    m_low = 0.0
    m_high = 0.0
    for j, m in enumerate(support, start=1):
        t = covered_transition_bounds(
            float(c[j - 1]),
            float(l[j]),
            float(h[j]),
            float(c[j]),
            m,
        )
        tv_low += t["tv_low"]
        tv_high += t["tv_high"]
        m_low = max(m_low, t["m_low"])
        m_high = max(m_high, t["m_high"])

    if tv_high <= 0.0 or m_high <= 0.0:
        return {
            "schema": SCHEMA,
            "defined": False,
            "reason": "no_positive_hidden_movement_possible",
            "bound_class": "fully_enveloped_bound",
            "native_transition_count": b,
            "fine_step_count": n,
            "support_source_count_total": int(sum(support)),
            "gap_source_count_total": 0,
            "gap_transition_count": 0,
            "future_outcome_used": False,
            "trade_authority": False,
        }

    j_low = max(1.0 / n, m_low / tv_high)
    j_high = min(1.0, m_high / tv_low) if tv_low > 0 else 1.0
    if j_high < j_low:
        raise ValueError("inconsistent structural J bounds")
    prof = _profile_bounds(n, j_low, j_high)
    return {
        "schema": SCHEMA,
        "defined": True,
        "reason": None,
        "bound_class": "fully_enveloped_bound",
        "native_transition_count": b,
        "fine_step_count": n,
        "support_source_count_total": int(sum(support)),
        "gap_source_count_total": 0,
        "gap_transition_count": 0,
        "tv_low": float(tv_low),
        "tv_high": float(tv_high),
        "m_low": float(m_low),
        "m_high": float(m_high),
        "j_low": float(j_low),
        "j_high": float(j_high),
        **prof,
        "conditional_on_positive_total_variation": False,
        "future_outcome_used": False,
        "trade_authority": False,
    }
