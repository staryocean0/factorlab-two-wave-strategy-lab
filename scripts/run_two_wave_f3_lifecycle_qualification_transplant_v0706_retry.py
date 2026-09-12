#!/usr/bin/env python3
"""Implementation-only retry adapter for frozen v0.7.6 qualification transplant.

The first formal v0.7.6 run (34685420204) was invalidated by one aggregate
serialization bug: ``per_ordinal_published_raw_cell_hit_cases`` is a mapping
with string ordinal keys, but the base runner iterated the mapping itself and
therefore recorded ``[0, 1, 2, 3, 4]`` rather than its values.  This adapter
normalizes that representation only.  It does not change the frozen protocol,
qualification thresholds, publication/lifecycle identity, semantic gates, or
decision precedence.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_two_wave_f3_lifecycle_qualification_transplant_v0706 as base

INVALID_FORMAL_RUN_ID = 34685420204
INVALID_RESULT_COMMIT = "f3f47f115faf54fb688dcb26a86998b6daa49169"
_ORIGINAL_SUMMARIZE_PUBLICATION_CASES = base.summarize_publication_cases
_ORIGINAL_MECHANICAL_UPSTREAM = base._mechanical_upstream


def ordered_ordinal_counts(value) -> list[int]:
    """Return ordinal-0..4 counts without confusing mapping keys for values."""
    if isinstance(value, dict):
        expected = {str(i) for i in range(5)}
        if set(value) != expected:
            raise ValueError(f"unexpected ordinal-count keys: {sorted(value)}")
        return [int(value[str(i)]) for i in range(5)]
    out = [int(x) for x in value]
    if len(out) != 5:
        raise ValueError("exactly five ordinal counts required")
    return out


def _normalized_summarize_publication_cases(records):
    summary = _ORIGINAL_SUMMARIZE_PUBLICATION_CASES(records)
    sem = summary["semantic_continuity"]
    sem["per_ordinal_published_raw_cell_hit_cases"] = ordered_ordinal_counts(
        sem["per_ordinal_published_raw_cell_hit_cases"]
    )
    return summary


def _normalized_mechanical_upstream(case_rows, formal_v0705):
    out = _ORIGINAL_MECHANICAL_UPSTREAM(case_rows, formal_v0705)
    out["published_raw_ordinal_hit_cases"] = ordered_ordinal_counts(
        formal_v0705["semantic_continuity"]["per_ordinal_published_raw_cell_hit_cases"]
    )
    return out


def main() -> int:
    base.summarize_publication_cases = _normalized_summarize_publication_cases
    base._mechanical_upstream = _normalized_mechanical_upstream
    rc = int(base.main())
    if rc != 0:
        return rc

    result_path = base.OUTPUT_DIR / "RESULT.json"
    result = json.loads(result_path.read_text())
    result["implementation_retry"] = {
        "original_invalid_formal_run_id": INVALID_FORMAL_RUN_ID,
        "original_invalid_result_commit": INVALID_RESULT_COMMIT,
        "retry_reason": "ordinal_count_mapping_keys_were_iterated_instead_of_values",
        "scientific_protocol_unchanged": True,
        "qualification_thresholds_changed": False,
        "frozen_decision_gates_changed": False,
        "publication_or_lifecycle_identity_changed": False,
        "direction_scoring_added": False,
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
