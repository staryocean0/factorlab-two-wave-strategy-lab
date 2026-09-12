#!/usr/bin/env python3
"""Retired writer; retain only the historical pure API for regression tests.

The original writer and authority are pinned archive snapshots. No CLI invocation
may roll the current control plane back to v0.7.7. Historical schema 1.32 results
returned by updated_authority are replay evidence, never current authority.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

if __name__ == "__main__":
    print("RETIRED: v0.7.7 governance is closed. Read CONTINUE_HERE.md; use scripts/verify_repository.py.", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
_ARCHIVE = ROOT / "docs/archive/repository_consistency_20260912"
_SPEC = importlib.util.spec_from_file_location("_two_wave_v0707_historical_governance", _ARCHIVE / "close_two_wave_v0707_governance.py")
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Historical v0.7.7 governance snapshot is unavailable")
_LEGACY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_LEGACY)
_LEGACY.ROOT = ROOT
RESULT_PATH = ROOT / "experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT.json"
ADJUDICATION_PATH = ROOT / "experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json"
AUTHORITY_PATH = _ARCHIVE / "two_wave_m0_authority.v1_32.json"
_LEGACY.RESULT_PATH = RESULT_PATH
_LEGACY.ADJUDICATION_PATH = ADJUDICATION_PATH
_LEGACY.AUTHORITY_PATH = AUTHORITY_PATH
EXPECTED_CATEGORY = _LEGACY.EXPECTED_CATEGORY
verify_formal_result = _LEGACY.verify_formal_result


def updated_authority(authority: dict, result: dict) -> dict:
    """Reproduce historical closure on a copy; never write current files."""
    return _LEGACY.updated_authority(copy.deepcopy(authority), result)
