import copy
import math
from datetime import datetime, timedelta, timezone

from factor_lab.visual_structure.two_wave.f3_lifecycle_qualification_transplant_v0706 import (
    PrefixBars,
    publication_identity_hash,
    qualification_contract_violations,
    qualify_publication,
    summarize_case_semantics,
)


def make_bars(n=40):
    start = datetime(2020, 1, 2, 1, 30, tzinfo=timezone.utc)
    closes = [100.0 + 0.02 * i for i in range(n)]
    pivots = {2: 100.0, 8: 110.0, 14: 101.0, 20: 111.0, 26: 102.0}
    for i, value in pivots.items():
        closes[i] = value
    out = []
    for i, close in enumerate(closes):
        ts = (start + timedelta(minutes=5 * i)).isoformat()
        out.append(
            {
                "bar_index": i,
                "timestamp": ts,
                "available_at": ts,
                "effective_information_time": ts,
                "trading_day": "2020-01-02",
                "open": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "log_close": math.log(close),
            }
        )
    return out


def make_publication():
    raw = [2, 8, 14, 20, 26]
    kinds = ["low", "high", "low", "high", "low"]
    return {
        "object_id": "obj-a",
        "object_key": ("r0", "r1", "r2", "r3", "r4"),
        "publication_id": "pub-a",
        "first_observation_bar": 28,
        "publishing_evidence_bar": 28,
        "publishing_level": 0,
        "predecessor_ridge_id": "pred",
        "phase": "low",
        "raw_occurrence_bars": raw,
        "points": [
            {"pivot_id": f"p{i}", "kind": kind, "occurrence_bar": bar}
            for i, (kind, bar) in enumerate(zip(kinds, raw))
        ],
        "status_at_publication": "observed_live_unresolved",
    }


def test_prefix_bars_hides_future_length_and_indices():
    bars = make_bars()
    prefix = PrefixBars(bars, 29)
    assert len(prefix) == 29
    assert prefix[28]["bar_index"] == 28
    assert [x["bar_index"] for x in prefix[26:29]] == [26, 27, 28]
    try:
        _ = prefix[29]
        assert False, "future bar must be inaccessible"
    except IndexError:
        pass


def test_future_bar_perturbation_cannot_change_qualification_or_identity():
    bars = make_bars()
    altered = copy.deepcopy(bars)
    for row in altered[29:]:
        row["close"] = row["close"] * 10.0
        row["high"] = row["close"] + 5.0
        row["low"] = row["close"] - 5.0
        row["open"] = row["close"]
        row["log_close"] = math.log(row["close"])

    publication = make_publication()
    before = publication_identity_hash(publication)
    original = qualify_publication(publication, bars)
    perturbed = qualify_publication(publication, altered)
    after = publication_identity_hash(publication)

    assert original["v054"] == perturbed["v054"]
    assert original["v0618"] == perturbed["v0618"]
    assert original["contract_violations"] == {}
    assert perturbed["contract_violations"] == {}
    assert original["identity_mutated"] is False
    assert perturbed["identity_mutated"] is False
    assert before == after


def test_v0618_contract_allows_only_registered_path_demotions():
    bars = make_bars()
    publication = make_publication()
    out = qualify_publication(publication, bars)
    assert out["contract_violations"] == {}
    old = out["v054"]["v054_hard_rejection_reasons"]
    new = out["v0618"]["v0618_hard_rejection_reasons"]
    assert all(reason in old for reason in new)
    assert set(old) - set(new) <= {"inefficient_leg", "jump_dominated_leg"}
    assert not (out["v054"]["scale_qualified"] and not out["v0618"]["scale_qualified"])

    broken = copy.deepcopy(out["v0618"])
    broken["v0618_hard_rejection_reasons"] = [
        reason for reason in broken["v054_hard_rejection_reasons"] if reason != "long_cycle"
    ]
    violations = qualification_contract_violations(out["v054"], broken)
    if "long_cycle" in out["v054"]["v054_hard_rejection_reasons"]:
        assert violations.get("v0618_removed_non_demoted_reason", 0) == 1


def test_qualified_semantic_support_uses_immutable_publication_only():
    key = ("r0", "r1", "r2", "r3", "r4")
    publication = {
        "states": {
            key: {
                "publication": {
                    "phase": "low",
                    "raw_occurrence_bars": [10, 20, 30, 40, 50],
                }
            }
        }
    }
    lifecycle = {
        "final_live_keys": {key},
        "objects": {key: {"certified": False}},
    }
    q = {
        key: {
            "v054": {"scale_qualified": False},
            "v0618": {"scale_qualified": True},
        }
    }
    cells = [(9, 11), (19, 21), (29, 31), (39, 41), (49, 51)]
    kinds = ["low", "high", "low", "high", "low"]
    out = summarize_case_semantics(publication, lifecycle, q, cells, kinds)
    assert out["published_raw_support"] is True
    assert out["v054_qualified_semantic_support"] is False
    assert out["v0618_qualified_semantic_support"] is True
    assert out["final_unresolved_v0618_qualified_raw_support"] is True
