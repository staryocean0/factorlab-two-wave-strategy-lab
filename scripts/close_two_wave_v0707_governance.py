#!/usr/bin/env python3
"""Retired writer. Only pure historical v0.7.7 snapshot helpers remain importable."""
from copy import deepcopy
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
_OLD = runpy.run_path(str(ROOT / "archive/control_plane_20260912/scripts/close_two_wave_v0707_governance.py"))
RESULT_PATH = ROOT / "experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT.json"
ADJUDICATION_PATH = ROOT / "experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json"
AUTHORITY_PATH = ROOT / "experiments/two_wave_m0_authority.json"
EXPECTED_CATEGORY = _OLD["EXPECTED_CATEGORY"]
verify_formal_result = _OLD["verify_formal_result"]


def updated_authority(authority: dict, result: dict) -> dict:
    """Build a historical snapshot without mutating caller data or the repository."""
    return _OLD["updated_authority"](deepcopy(authority), deepcopy(result))


def main() -> int:
    raise SystemExit("RETIRED: v0.7.7 closure may not overwrite current authority; read CONTINUE_HERE.md")


if __name__ == "__main__":
    main()
