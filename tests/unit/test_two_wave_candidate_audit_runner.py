"""Exercise the candidate audit pipeline on synthetic input before full replay."""
from __future__ import annotations

import copy
import importlib.util
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest


def test_audit_runner_end_to_end_synthetic(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/run_two_wave_candidate_audit.py"
    spec = importlib.util.spec_from_file_location("candidate_audit_test", script)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    logs = np.interp(np.arange(91), [0, 2, 3, 4, 23, 24, 26, 40, 55, 70, 90],
                     [4.05, 4, 4.021, 4.002, 4.041, 4.022, 4.05, 4, 4.04, 4.01, 4.06])
    bars = []
    for i, x in enumerate(logs):
        stamp = (datetime(2015, 1, 5, tzinfo=UTC) + timedelta(minutes=i)).isoformat()
        p = float(np.exp(x))
        bars.append({"timestamp": stamp, "available_at": stamp,
                     "open": p, "high": p, "low": p, "close": p})
    original = copy.deepcopy(bars)
    engines = {}
    for method in audit.METHODS:
        engine, prefix = audit.replay(bars, method, "synthetic", .01)
        engines[method] = engine
        result = audit.describe(engine, prefix)
        assert prefix["passed"]
        assert result["candidate_count"] == len(engine.structures)
        unchanged = audit.perturb_compare(engine, engine)
        assert unchanged["baseline_unmatched"] == 0
        assert unchanged["matched_classification_changes"] == 0
        altered, _ = audit.replay(audit.perturb(bars), method, "synthetic", .01)
        audit.perturb_compare(engine, altered)
    for method in audit.VARIANTS:
        result = audit.compare_same_input(engines["v01"], engines[method])
        assert result["geometric_breakouts_identical"]
        assert sum(result["classification_transitions"].values()) == len(engines[method].structures)
    pool = defaultdict(list)
    audit.collect_cases(pool, engines, "synthetic", .01)
    gallery = audit.make_gallery(tmp_path / "gallery", pool)
    assert gallery["case_count"] > 0
    assert (tmp_path / "gallery/index.html").is_file()
    assert len(list((tmp_path / "gallery").glob("*.svg"))) == gallery["case_count"]
    assert bars == original
    with pytest.raises(ValueError):
        audit.new_engine("unknown", "synthetic", .01)
