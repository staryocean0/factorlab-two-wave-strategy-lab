from pathlib import Path
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_broad_rmr_stage1_R1_R2_R3 as base
import run_broad_rmr_M1_R1_R2_outcomes as m1out


def parent(direction=1, conf=0, amp=0.10, failure=-0.20, low=-0.20, high=0.20, day="2018-01-02"):
    return base.Geo(
        ident=f"p{direction}_{conf}", phase="low" if direction > 0 else "high", level=5,
        conf=conf, occ=(0, 12, 24, 36, 48), day=day,
        direction=direction, amp=amp, abs_drift=0.5, overlap=0.2,
        eff=0.6, low=low, high=high, failure=failure, span=48,
    )


def test_r1_positive_parent_recovery_boundary_is_upper_and_failure_lower():
    p = parent(direction=1, amp=0.10, failure=-0.20)
    # Trigger at idx 4 after running max .03 and 0.05 drawdown; recover at idx 6.
    logp = np.array([0.00, 0.02, 0.03, 0.00, -0.02, 0.00, 0.031, -0.30])
    days = np.array(["2018-01-02"] * len(logp))
    frame, reasons = m1out.r1_outcomes([p], logp, days, {2018: len(logp) - 1})
    assert reasons["triggered"] == 1
    assert len(frame) == 1
    assert frame.iloc[0].outcome == "recovery"


def test_r1_negative_parent_recovery_boundary_is_lower_and_failure_upper():
    p = parent(direction=-1, amp=0.10, failure=0.20, low=-0.20, high=0.20)
    # Running min -.03, rebound to .02 triggers; then returns below -.03.
    logp = np.array([0.00, -0.02, -0.03, 0.00, 0.02, 0.00, -0.031, 0.30])
    days = np.array(["2018-01-02"] * len(logp))
    frame, reasons = m1out.r1_outcomes([p], logp, days, {2018: len(logp) - 1})
    assert reasons["triggered"] == 1
    assert len(frame) == 1
    assert frame.iloc[0].outcome == "recovery"


def test_r2_upper_excursion_reentry_is_lower_boundary():
    p = parent(direction=1, amp=0.10, failure=-0.20, low=-0.10, high=0.10)
    logp = np.array([0.00, 0.11, 0.105, 0.099, 0.20])
    days = np.array(["2018-01-02"] * len(logp))
    frame = m1out.r2_outcomes([p], logp, days, {2018: len(logp) - 1})
    assert len(frame) == 1
    assert frame.iloc[0].outcome == "reentry"


def test_r2_lower_excursion_reentry_is_upper_boundary():
    p = parent(direction=-1, amp=0.10, failure=0.20, low=-0.10, high=0.10)
    logp = np.array([0.00, -0.11, -0.105, -0.099, -0.20])
    days = np.array(["2018-01-02"] * len(logp))
    frame = m1out.r2_outcomes([p], logp, days, {2018: len(logp) - 1})
    assert len(frame) == 1
    assert frame.iloc[0].outcome == "reentry"


def test_parent_expiry_and_year_end_can_censor_outcome():
    p = parent(direction=1, amp=0.10, failure=-0.20)
    # Trigger at final allowed index, leaving no post-trigger observation.
    logp = np.array([0.00, 0.03, -0.02])
    days = np.array(["2018-12-31"] * len(logp))
    frame, _ = m1out.r1_outcomes([p], logp, days, {2018: 2})
    assert len(frame) == 1
    assert frame.iloc[0].outcome == "censored"


def test_protocol_keeps_R3_closed_and_all_parameters_frozen():
    p = json.loads((ROOT / "docs/governance/reversal_mean_reversion_M1_R1_R2_outcome_protocol_v1.json").read_text())
    assert p["R1"]["shock_fraction"] == 0.5
    assert p["R1"]["shock_fraction_search"] is False
    assert p["R2"]["additional_excursion_threshold"] is None
    assert p["source"]["parent_birth_level"] == 5
    assert p["source"]["post_2020_open"] is False


def test_runner_never_reopens_R3_or_searches_thresholds():
    source = (ROOT / "scripts/run_broad_rmr_M1_R1_R2_outcomes.py").read_text()
    assert '"R3_reopened": False' in source
    assert '"shock_fraction_search_performed": False' in source
    assert '"excursion_threshold_search_performed": False' in source
    assert '"post_2020_rows_read": False' in source
