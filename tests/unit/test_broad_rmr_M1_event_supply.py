from pathlib import Path
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_broad_rmr_stage1_R1_R2_R3 as base
import inventory_broad_rmr_M1_event_supply as m1


def parent(direction=1, amp=0.10, failure=-0.20, low=-0.20, high=0.20):
    return base.Geo(
        ident="p", phase="low" if direction > 0 else "high", level=5,
        conf=0, occ=(0, 12, 24, 36, 48), day="2018-01-02",
        direction=direction, amp=amp, abs_drift=0.5, overlap=0.2,
        eff=0.6, low=low, high=high, failure=failure, span=48,
    )


def test_r1_positive_parent_triggers_at_frozen_half_amplitude():
    p = parent(direction=1, amp=0.10, failure=-0.20)
    # Running extreme rises to .03, then drawdown reaches .05 at index 4.
    logp = np.array([0.00, 0.02, 0.03, 0.00, -0.02, -0.03])
    event, reason = m1.find_r1_trigger(logp, p, 5)
    assert reason == "triggered"
    assert event["event_idx"] == 4
    assert np.isclose(event["severity"], 0.5)
    assert np.isclose(event["recovery_boundary"], 0.03)


def test_r1_aborts_if_parent_failure_arrives_before_shock_trigger():
    p = parent(direction=1, amp=0.50, failure=-0.05)
    logp = np.array([0.00, -0.02, -0.051, -0.06])
    event, reason = m1.find_r1_trigger(logp, p, 3)
    assert event is None
    assert reason == "parent_failure_before_trigger"


def test_r2_uses_first_strict_close_outside_frozen_envelope():
    p = parent(direction=1, amp=0.10, failure=-0.20, low=-0.10, high=0.10)
    logp = np.array([0.00, 0.05, 0.10, 0.101, 0.20])
    event = m1.find_r2_trigger(logp, p, 4)
    assert event["event_idx"] == 3
    assert event["side"] == 1
    assert np.isclose(event["outside_distance"], 0.001)


def test_role_counts_match_frozen_build_and_check_windows():
    events = [
        {"day": "2018-12-31"},
        {"day": "2019-01-02"},
        {"day": "2020-12-31"},
    ]
    assert m1.role_counts(events) == {
        "BUILD_2015_2018": 1,
        "CHECK_2019": 1,
        "CHECK_2020": 1,
    }


def test_M1_adapter_locks_supply_only_and_frozen_threshold_source():
    cfg = json.loads((ROOT / "docs/governance/reversal_mean_reversion_M1_single_shock_event_adapter_v1.json").read_text())
    assert cfg["M1_S0_supply_only"]["post_event_outcomes_read"] is False
    assert cfg["R1_single_counter_shock"]["shock_threshold"] == "0.5_times_parent_amplitude_scale"
    assert "v043_MaturityConfig_amplitude_ratio_2.0" in cfg["R1_single_counter_shock"]["threshold_source"]
    assert cfg["R2_first_envelope_excursion"]["additional_excursion_threshold"] is None
    assert cfg["source"]["post_2020_open"] is False


def test_supply_script_cannot_construct_post_trigger_first_passage_outcomes():
    source = (ROOT / "scripts/inventory_broad_rmr_M1_event_supply.py").read_text()
    assert "first_passage(" not in source
    assert "base.r1_events(" not in source
    assert "base.r2_events(" not in source
    assert '"post_event_outcomes_read": False' in source
    assert 'SHOCK_FRACTION = 0.5' in source
