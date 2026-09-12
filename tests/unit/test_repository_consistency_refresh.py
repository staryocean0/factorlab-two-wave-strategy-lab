import json
from pathlib import Path

from factor_lab.visual_structure.two_wave.repository_consistency import (
    AUTHORITY_SCHEMA,
    GLOBAL_STATUS,
    updated_authority,
    validate_current_authority,
    verify_v0708_adjudication,
)

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = ROOT / "experiments/two_wave_m0_authority.json"
ADJUDICATION_PATH = ROOT / "experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json"


def _load(path: Path):
    return json.loads(path.read_text())


def test_v0708_adjudication_is_eligible_for_repository_refresh():
    verify_v0708_adjudication(_load(ADJUDICATION_PATH))


def test_refresh_promotes_authority_without_promoting_scientific_authority():
    refreshed = updated_authority(_load(AUTHORITY_PATH), _load(ADJUDICATION_PATH))
    validate_current_authority(refreshed)

    assert refreshed["schema"] == AUTHORITY_SCHEMA
    assert refreshed["global_status"] == GLOBAL_STATUS
    assert refreshed["morphology_acceptance"] is False
    assert refreshed["component_authority"]["parent_identity"]["active_semantic_parent_authority"] is None
    assert refreshed["component_authority"]["parent_direction"]["winner"] is None
    assert refreshed["no_current_direction_challenger_authorized"] is True

    v0708 = refreshed["external_validation_availability"]["v0708"]
    assert v0708["connected_repository_count"] == 7
    assert v0708["new_temporal_evidence_available"] is False
    assert v0708["new_independent_reference_label_evidence_available"] is False
    assert v0708["both_reopening_requirements_satisfied"] is False
    assert v0708["candidate_opened"] is False


def test_refresh_preserves_v0707_direction_evidence_and_external_blocks():
    current = _load(AUTHORITY_PATH)
    refreshed = updated_authority(current, _load(ADJUDICATION_PATH))

    before = current["component_authority"]["parent_direction"]["v0707"]
    after = refreshed["component_authority"]["parent_direction"]["v0707"]
    assert after == before
    assert after["v0625_rescue_count"] == 19
    assert after["D1_case_exact_count"] == 7
    assert after["v0625_case_exact_count"] == 7
    assert after["v0647_external_validation_blocked"] is True
    assert after["v0648_external_validation_blocked"] is True
