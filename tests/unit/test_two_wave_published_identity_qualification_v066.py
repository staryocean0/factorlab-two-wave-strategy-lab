from datetime import datetime, timedelta, timezone

from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import (
    qualify_published_raw_identity,
    v054_hard_reasons,
)
from factor_lab.visual_structure.two_wave.scale_invariant_predecessor_publication_v065 import (
    publish_first_valid_candidate,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig


def bars():
    n = 40
    anchors = {2: 100.0, 8: 110.0, 14: 101.0, 20: 111.0, 26: 102.0}
    close = [0.0] * n
    keys = sorted(anchors)
    for a, b in zip(keys, keys[1:]):
        for i in range(a, b + 1):
            u = (i - a) / (b - a)
            close[i] = anchors[a] + u * (anchors[b] - anchors[a])
    for i in range(keys[0]):
        close[i] = anchors[keys[0]]
    for i in range(keys[-1], n):
        close[i] = anchors[keys[-1]]
    start = datetime(2020, 1, 2, 1, 30, tzinfo=timezone.utc)
    out = []
    for i, x in enumerate(close):
        ts = (start + timedelta(minutes=5 * i)).isoformat()
        out.append({"timestamp": ts, "available_at": ts, "close": x})
    return out


def test_frozen_published_identity_has_deterministic_qualification():
    out = qualify_published_raw_identity("low", [2, 8, 14, 20, 26], 30, bars(), MaturityConfig())
    assert out["scale_qualified"] is True
    assert out["v054_hard_rejection_reasons"] == []


def test_future_append_after_confirmation_does_not_change_qualification():
    base = bars()
    a = qualify_published_raw_identity("low", [2, 8, 14, 20, 26], 30, base, MaturityConfig())
    extra = base + [{"timestamp": "2020-01-03T00:00:00+00:00", "available_at": "2020-01-03T00:00:00+00:00", "close": 999999.0}]
    b = qualify_published_raw_identity("low", [2, 8, 14, 20, 26], 30, extra, MaturityConfig())
    assert a == b


def test_v054_demotes_only_corresponding_leg_reason():
    assert v054_hard_reasons(["corresponding_leg_duration_mismatch"]) == []


def test_every_other_frozen_reason_remains_hard():
    reasons = ["inefficient_leg", "corresponding_leg_duration_mismatch", "jump_dominated_leg"]
    assert v054_hard_reasons(reasons) == ["inefficient_leg", "jump_dominated_leg"]


def test_later_divergent_scale_evidence_cannot_change_qualification_input():
    evidence = [
        {"event_id": "a", "birth_confirmation_bar": 30, "birth_level": 2, "valid": True, "reason": None, "raw_occurrence_bars": [2, 8, 14, 20, 26], "predecessor_occurrence_bar": 1, "predecessor_confirmation_bar": 2},
        {"event_id": "b", "birth_confirmation_bar": 31, "birth_level": 3, "valid": True, "reason": None, "raw_occurrence_bars": [3, 8, 14, 20, 26], "predecessor_occurrence_bar": 2, "predecessor_confirmation_bar": 3},
    ]
    pub = publish_first_valid_candidate("low", [4, 9, 15, 21, 27], evidence)
    raw = pub["publication_event"]["published_raw_occurrence_bars"]
    assert raw == [2, 8, 14, 20, 26]
    q = qualify_published_raw_identity("low", raw, pub["publication_event"]["publishing_birth_confirmation_bar"], bars(), MaturityConfig())
    assert q["scale_qualified"] is True
    assert pub["suppressed_would_be_rewrite_count"] == 1
