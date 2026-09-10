"""Read-only v0.6.32 attribution helpers for rejected v0.6.31 Range rescue."""
from __future__ import annotations

from typing import Mapping

import numpy as np

SCHEMA = "two_wave_v0631_residual_attribution@0.6.32"
SUPPORT_NAMES = ("full", "left_eroded_1", "right_eroded_1", "both_eroded_1")
EPS = 1e-12


def classify_one_sided_change(old_pair: tuple[str, str], new_pair: tuple[str, str]) -> str:
    changed = [a != b for a, b in zip(old_pair, new_pair)]
    if sum(changed) != 1:
        raise ValueError("v0.6.32 semantic class requires exactly one changed side")
    if old_pair[0] == old_pair[1] and new_pair[0] != new_pair[1]:
        return "introduced_harm"
    if old_pair[0] != old_pair[1] and new_pair[0] == new_pair[1]:
        return "repaired_old_nonexact"
    if old_pair[0] != old_pair[1] and new_pair[0] != new_pair[1]:
        return "neutral_nonexact"
    raise AssertionError("unreachable one-sided topology")


def support_containment_slacks(detail: Mapping[str, float]) -> dict[str, float]:
    q1_lo = float(detail["cycle1_q25"])
    m1 = float(detail["cycle1_median"])
    q1_hi = float(detail["cycle1_q75"])
    q2_lo = float(detail["cycle2_q25"])
    m2 = float(detail["cycle2_median"])
    q2_hi = float(detail["cycle2_q75"])
    w1 = q1_hi - q1_lo
    w2 = q2_hi - q2_lo
    if not np.isfinite([q1_lo, m1, q1_hi, q2_lo, m2, q2_hi]).all() or min(w1, w2) <= EPS:
        raise ValueError("finite nondegenerate cycle IQRs required")
    s12 = min(m1 - q2_lo, q2_hi - m1) / w2
    s21 = min(m2 - q1_lo, q1_hi - m2) / w1
    return {
        "cycle1_median_in_cycle2_iqr_slack": float(s12),
        "cycle2_median_in_cycle1_iqr_slack": float(s21),
        "support_min_slack": float(min(s12, s21)),
    }


def summarize_support_slacks(support_details: Mapping[str, Mapping[str, float]]) -> dict:
    rows = {name: support_containment_slacks(support_details[name]) for name in SUPPORT_NAMES}
    all_slacks = []
    for name in SUPPORT_NAMES:
        all_slacks.extend([
            rows[name]["cycle1_median_in_cycle2_iqr_slack"],
            rows[name]["cycle2_median_in_cycle1_iqr_slack"],
        ])
    owner = min(SUPPORT_NAMES, key=lambda name: (rows[name]["support_min_slack"], name))
    return {
        "support_slacks": rows,
        "min_containment_slack_iqr": float(min(all_slacks)),
        "median_containment_slack_iqr": float(np.median(np.asarray(all_slacks, dtype=float))),
        "min_slack_support": owner,
    }
