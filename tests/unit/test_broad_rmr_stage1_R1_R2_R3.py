from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_broad_rmr_stage1_R1_R2_R3 as rmr


def test_maturity_uses_frozen_12_48_96_bounds():
    assert rmr.mature([0, 6, 12, 18, 24]) is True
    assert rmr.mature([0, 5, 11, 17, 23]) is False
    assert rmr.mature([0, 24, 48, 72, 96]) is True
    assert rmr.mature([0, 25, 49, 74, 98]) is False


def test_same_confirmation_bar_dedup_is_lexicographic_and_outcome_blind():
    x = pd.DataFrame(
        [
            {"publishing_birth_level": 5, "published_raw_occurrence_bars": [0, 6, 12, 18, 24], "publishing_birth_confirmation_bar": 30, "canonical_filtered_identity_id": "z"},
            {"publishing_birth_level": 5, "published_raw_occurrence_bars": [1, 7, 13, 19, 25], "publishing_birth_confirmation_bar": 30, "canonical_filtered_identity_id": "a"},
            {"publishing_birth_level": 5, "published_raw_occurrence_bars": [2, 8, 14, 20, 26], "publishing_birth_confirmation_bar": 31, "canonical_filtered_identity_id": "b"},
        ]
    )
    out = rmr.dedup_level(x, 5)
    assert list(out["canonical_filtered_identity_id"]) == ["a", "b"]


def test_binary_labels_are_explicit_for_all_three_lanes():
    frame = pd.DataFrame(
        {
            "day": ["2018-01-01"] * 8,
            "x": np.arange(8, dtype=float),
            "outcome": [
                "recovery", "failure", "censored",
                "reentry", "continuation",
                "failure", "extension", "tie",
            ],
        }
    )
    r1 = rmr.binary_frame(frame, ["x"], "recovery", "failure")
    assert list(r1["outcome"]) == ["recovery", "failure", "failure"]
    assert list(r1["y"]) == [1, 0, 0]

    r2 = rmr.binary_frame(frame, ["x"], "reentry", "continuation")
    assert list(r2["outcome"]) == ["reentry", "continuation"]
    assert list(r2["y"]) == [1, 0]

    r3 = rmr.binary_frame(frame, ["x"], "failure", "extension")
    assert list(r3["outcome"]) == ["failure", "failure", "extension"]
    assert list(r3["y"]) == [1, 1, 0]


def test_first_passage_respects_directional_labels_and_censor_end():
    logp = np.array([0.00, 0.02, 0.04, 0.01, -0.03, 0.08])
    outcome, idx = rmr.first_passage(logp, 0, 4, 0.05, -0.02, "up", "down")
    assert (outcome, idx) == ("down", 4)

    outcome, idx = rmr.first_passage(logp, 0, 3, 0.05, -0.02, "up", "down")
    assert (outcome, idx) == ("censored", 3)


def test_year_end_indices_make_each_year_local():
    days = np.array(["2018-12-28", "2018-12-31", "2019-01-02", "2019-12-31", "2020-01-02"])
    ends = rmr.year_end_indices(days)
    assert ends[2018] == 1
    assert ends[2019] == 3
    assert ends[2020] == 4


def test_protocol_locks_levels_and_post2020_boundary():
    adapter = json.loads((ROOT / "docs/governance/reversal_mean_reversion_stage1_event_adapter_v1.json").read_text())
    censor = json.loads((ROOT / "docs/governance/reversal_mean_reversion_stage1_partition_censor_v1.json").read_text())
    assert adapter["scale_binding"]["parent_birth_level"] == 5
    assert adapter["scale_binding"]["finer_birth_level"] == 3
    assert adapter["scale_binding"]["scale_search_after_freeze"] is False
    assert adapter["source"]["post_2020_open"] is False
    assert censor["CHECK"]["2019_event_outcomes_must_not_use_2020_rows"] is True
    assert censor["CHECK"]["2020_event_outcomes_must_not_use_post_2020_rows"] is True


def test_runner_uses_explicit_R2_continuation_negative_label():
    source = (ROOT / "scripts/run_broad_rmr_stage1_R1_R2_R3.py").read_text()
    assert "evaluate_lane(R2,r2_models,'reentry','continuation')" in source
    assert "fit_model(build,features,positive,negative)" in source
    assert "b.trading_day.max()>CHECK_END" in source
