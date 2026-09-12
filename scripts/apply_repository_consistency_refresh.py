from __future__ import annotations

import json
from pathlib import Path

from factor_lab.visual_structure.two_wave.repository_consistency import (
    updated_authority,
    validate_current_authority,
    verify_v0708_adjudication,
)

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "experiments/two_wave_m0_authority.json"
ADJUDICATION_PATH = ROOT / "experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json"
STATUS_PATH = ROOT / "docs/governance/repository_component_status.json"


def main() -> None:
    current = json.loads(AUTHORITY_PATH.read_text())
    adjudication = json.loads(ADJUDICATION_PATH.read_text())
    verify_v0708_adjudication(adjudication)

    authority = updated_authority(current, adjudication)
    validate_current_authority(authority)
    AUTHORITY_PATH.write_text(json.dumps(authority, ensure_ascii=False, indent=2) + "\n")

    status = {
        "schema": "two_wave_repository_component_status@1.0",
        "date": "2026-09-12",
        "authority_schema": authority["schema"],
        "global_status": authority["global_status"],
        "active_workflow_surface": [".github/workflows/ci.yml"],
        "current_scientific_chain": [
            "v0.7.1 F3 persistence-dominant semantic objectization",
            "v0.7.4 prefix-causal lifecycle",
            "v0.7.5 immutable provisional lifecycle publication",
            "v0.7.6 v0.6.18 qualification transplant",
            "v0.7.7 D1/v0.6.25 direction transplant (Development only)",
            "v0.7.8 external-validation evidence availability audit",
        ],
        "historical_reproducibility_assets_retained": True,
        "one_shot_workflows_retained": False,
        "direction_winner": None,
        "active_semantic_parent_authority": None,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
        "next_reopening_requires": [
            "genuinely new temporal evidence not previously consumed by v0.6.47 or later validation",
            "independently frozen Two-Wave morphology/reference labels created before model scoring",
        ],
        "canonical_entrypoints": {
            "human_readable_current_state": "README.md",
            "research_index": "docs/INDEX.md",
            "machine_authority": "experiments/two_wave_m0_authority.json",
            "human_authority_snapshot": "docs/research/TWO_WAVE_M0_AUTHORITY.md",
            "external_evidence_audit": "docs/research/TWO_WAVE_EXTERNAL_VALIDATION_EVIDENCE_AVAILABILITY_V0708.md",
            "external_evidence_adjudication": "experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json",
        },
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
