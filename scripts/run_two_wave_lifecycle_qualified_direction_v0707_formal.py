#!/usr/bin/env python3
"""Formal entrypoint for v0.7.7 with exact authoritative v0.7.6 gate names."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_two_wave_lifecycle_qualified_direction_v0707 as base


def authoritative_v0706_supported(result: dict) -> bool:
    try:
        decision = result["frozen_decision"]
        return (
            result["primary_category"]
            == "v0706_v0618_lifecycle_qualification_transplant_supported"
            and int(result["required_upstream_replication"]["published_lifecycle_object_count"]) == 1543
            and int(result["interface_audit"]["v054_exception_count"]) == 0
            and int(result["interface_audit"]["v0618_exception_count"]) == 0
            and int(result["qualification_summary"]["contract_violation_count"]) == 0
            and int(result["qualification_summary"]["v0618"]["qualified_count"]) == 115
            and int(result["semantic_transplant"]["v0618_qualified_semantic_support_cases"]) == 9
            and bool(decision["interface_gate_passed"])
            and bool(decision["v0618_contract_gate_passed"])
            and bool(decision["semantic_support_gate_passed"])
            and bool(decision["upstream_replication_ok"])
        )
    except (KeyError, TypeError, ValueError):
        return False


def main() -> int:
    base.formal_v0706_authority_ok = authoritative_v0706_supported
    return int(base.main())


if __name__ == "__main__":
    raise SystemExit(main())
