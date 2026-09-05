#!/usr/bin/env python3
"""Performance-only shim for the frozen v0.5 TCSS POC runner.

The original runner counts v0.4.3 audit-overlay pivots inside every TCSS
candidate with a full boolean scan.  This shim replaces only that equivalent
count with binary searches on the already sorted occurrence bars.  No scale,
filter, extrema, candidate, prefix, case, qualification, D1, or decision logic
is changed.
"""
from __future__ import annotations

import numpy as np

import run_two_wave_multiscale_tcss_poc as study


def fast_local_overlay(candidates, local_pivots):
    bars = np.asarray(
        [p["occurrence_bar"] for p in local_pivots if not p.get("left_censored", False)],
        dtype=int,
    )
    counts = []
    excess = []
    for candidate in candidates:
        lo, hi = candidate.occurrence_indices[0], candidate.occurrence_indices[-1]
        count = int(np.searchsorted(bars, hi, side="right") - np.searchsorted(bars, lo, side="left"))
        counts.append(count)
        excess.append(max(0, count - 5))
    return {
        "v043_local_pivots_inside_candidate_quantiles": study.quantiles(counts),
        "v043_excess_local_pivots_beyond_five_quantiles": study.quantiles(excess),
        "candidates_with_at_least_one_excess_v043_local_pivot": int(sum(v > 0 for v in excess)),
    }


study.local_overlay = fast_local_overlay


if __name__ == "__main__":
    study.main()
