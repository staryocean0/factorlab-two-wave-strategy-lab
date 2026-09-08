from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_broad_rmr_stage1_R1_R2_R3 as base
import run_broad_rmr_R4_statistical_state as r4


def geo(ident, conf, eff=0.5, amp=0.1, day="2018-01-02", direction=1, failure=-0.2):
    return base.Geo(
        ident=ident, phase="low" if direction > 0 else "high", level=5,
        conf=conf, occ=(max(0, conf-48), max(0, conf-36), max(0, conf-24), max(0, conf-12), conf),
        day=day, direction=direction, amp=amp, abs_drift=0.5, overlap=0.2,
        eff=eff, low=-0.2, high=0.2, failure=failure, span=48,
    )


def test_robust_z_is_past_only_and_excludes_current_from_reference():
    vals = [float(i) for i in range(100)] + [1000.0]
    z = r4.robust_z_past(vals, 100)
    assert np.isnan(z[:100]).all()
    hist = np.arange(100, dtype=float)
    med = np.median(hist)
    mad = np.median(np.abs(hist - med))
    expected = (1000.0 - med) / (1.4826 * mad)
    assert np.isclose(z[100], expected)


def test_density_counts_only_strictly_prior_96_bars():
    parents = [geo("p", 200)]
    finers = [geo("f0", 104), geo("f1", 105), geo("f2", 150), geo("f3", 199), geo("f4", 200), geo("f5", 201)]
    density = r4.event_density(parents, finers)
    # Strict interval (104, 200): 105,150,199 only.
    assert density.tolist() == [3.0]


def test_state_orientation_is_fixed():
    parents = []
    # 101 parents so the final state is available; increasing efficiency should create positive z then negative inefficiency.
    for i in range(101):
        parents.append(geo(f"p{i}", i * 100 + 50, eff=0.1 + i * 0.001, amp=0.1 + i * 0.0001, day="2018-01-02"))
    states = r4.state_frame(parents, [])
    assert states.loc[100, "R4_A_inefficiency"] < 0
    assert states.loc[100, "R4_C_amplitude_extremity"] >= 0


def test_candidate_baseline_uses_same_candidate_available_rows():
    rows = []
    for i in range(220):
        year = "2018" if i < 160 else ("2019" if i < 190 else "2020")
        rows.append({
            "day": f"{year}-01-02",
            "conf": i,
            "abs_drift": 0.2 + 0.001 * i,
            "log_amplitude": -2.0 + 0.001 * i,
            "R4_A_inefficiency": (i - 100) / 50.0 if i >= 100 else np.nan,
            "R4_B_event_density": np.nan,
            "R4_C_amplitude_extremity": np.nan,
            "outcome": "failure" if i % 2 else "extension",
        })
    frame = pd.DataFrame(rows)
    result = r4.candidate_summary(frame, "R4_A_inefficiency")
    assert result["pooled"]["baseline"]["n"] == result["pooled"]["candidate"]["n"]
    assert result["annual"]["2019"]["baseline"]["n"] == result["annual"]["2019"]["candidate"]["n"]
    assert result["annual"]["2020"]["baseline"]["n"] == result["annual"]["2020"]["candidate"]["n"]


def test_positive_parent_failure_and_extension_boundaries_are_symmetric():
    p = geo("p", 0, direction=1, failure=-0.10)
    # Event 0, failure distance .10, extension +.10; path reaches failure first.
    logp = np.array([0.00, -0.02, -0.11, 0.20])
    days = np.array(["2018-01-02"] * len(logp))
    states = pd.DataFrame([{"ident": "p", "day": "2018-01-02", "conf": 0, "abs_drift": 0.5, "log_amplitude": -2.0,
                            "raw_parent_eff": 0.5, "raw_event_density": 0.0,
                            "R4_A_inefficiency": np.nan, "R4_B_event_density": np.nan, "R4_C_amplitude_extremity": np.nan}])
    out = r4.add_outcomes(states, [p], logp, days)
    assert out.iloc[0].outcome == "failure"


def test_protocol_locks_three_independent_candidates_and_no_post2020():
    p = json.loads((ROOT / "docs/governance/reversal_mean_reversion_R4_statistical_state_protocol_v1.json").read_text())
    assert [x["id"] for x in p["candidates"]] == list(r4.CANDIDATES)
    assert p["candidate_budget"]["objects"] == 3
    assert p["candidate_budget"]["combined_state_model"] is False
    assert p["past_only_normalization"]["reference_parent_count"] == 100
    assert p["candidates"][1]["density_window_bars"] == 96
    assert p["source"]["post_2020_open"] is False


def test_runner_does_not_combine_states_or_use_property_reversion_as_gate():
    source = (ROOT / "scripts/run_broad_rmr_R4_statistical_state.py").read_text()
    assert '"combined_state_model_used": False' in source
    assert '"property_self_reversion_used_for_progression": False' in source
    assert '"post_2020_rows_read": False' in source
    assert 'CANDIDATES = {' in source
