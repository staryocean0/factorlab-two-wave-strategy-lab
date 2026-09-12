import json
from pathlib import Path

from factor_lab.visual_structure.two_wave.repository_consistency import (
    GLOBAL_STATUS,
    validate_current_authority,
)

ROOT = Path(__file__).resolve().parents[2]


def _load(relative: str):
    return json.loads((ROOT / relative).read_text())


def test_current_authority_and_navigation_are_synchronized():
    authority = _load("experiments/two_wave_m0_authority.json")
    validate_current_authority(authority)

    status = _load("docs/governance/repository_component_status.json")
    assert status["authority_schema"] == authority["schema"] == "two_wave_m0_authority@1.33"
    assert status["global_status"] == authority["global_status"] == GLOBAL_STATUS
    assert status["direction_winner"] is None
    assert status["active_semantic_parent_authority"] is None
    assert status["morphology_acceptance"] is False
    assert status["trade_authority"] is False
    assert status["production_authority"] is False

    for relative in (
        "README.md",
        "docs/INDEX.md",
        "docs/research/TWO_WAVE_M0_AUTHORITY.md",
        "ai-readme.md",
    ):
        assert GLOBAL_STATUS in (ROOT / relative).read_text()


def test_package_scope_matches_actual_public_bounded_repository_role():
    scope = _load("docs/governance/package_scope.json")
    assert scope["schema_id"] == "two_wave_cloud_theme_package_scope@1.1"
    assert scope["package_role"] == "public_bounded_research_and_reproducibility_repository"
    assert scope["repository_visibility"] == "public"
    assert scope["private_repository_required"] is False
    assert scope["morphology_acceptance"] is False
    assert scope["trade_authority"] is False
    assert scope["production_authority"] is False
    assert scope["long_lived_workflow_surface"] == [".github/workflows/ci.yml"]


def test_data_usage_distinguishes_shipped_development_from_consumed_external_validation():
    usage = _load("docs/governance/data_usage_declaration.json")
    assert usage["schema_id"] == "two_wave_cloud_theme_data_usage@1.1"
    shipped = usage["shipped_development_intervals"]
    assert shipped == [
        {
            "start": "2015-01-05",
            "end": "2020-12-31",
            "role": "development_material",
            "allowed_uses": [
                "recognition_specification",
                "morphology_candidate_generation",
                "annotation_pack_generation",
                "causal_replay_debugging",
                "synthetic_and_real_data_property_tests",
                "formal_development_replay",
            ],
            "fresh_evidence": False,
        }
    ]
    consumed = usage["external_temporal_validation_history"]["consumed_slices"]
    assert [(row["start"], row["end"]) for row in consumed] == [
        ("2024-01-02", "2024-12-31"),
        ("2025-01-02", "2025-12-31"),
        ("2026-01-05", "2026-08-21"),
    ]
    availability = usage["current_external_evidence_availability"]
    assert availability["post_2026_08_21_CSI1000_minute_extension_available"] is False
    assert availability["new_independent_two_wave_reference_labels_available"] is False
    assert availability["direction_reopening_condition_satisfied"] is False


def test_workflow_surface_has_only_ci_or_explicit_transient_one_shots():
    workflows = sorted(path.name for path in (ROOT / ".github/workflows").glob("*.yml"))
    assert "ci.yml" in workflows
    assert all(name == "ci.yml" or name.endswith("-once.yml") for name in workflows)


def test_broad_parent_project_indexes_are_retired_as_current_authority():
    ai_entry = (ROOT / "ai-readme.md").read_text().lower()
    docs_entry = (ROOT / "docs/00-index.md").read_text().lower()
    ops_entry = (ROOT / "docs/ops/README.md").read_text().lower()
    user_entry = (ROOT / "docs/user/README.md").read_text().lower()
    assert "retired" in ai_entry
    assert "retired" in docs_entry
    assert "current authority lives elsewhere" in ops_entry
    assert "current research state" in user_entry


def test_v0708_has_human_and_machine_closure_surfaces():
    adjudication = _load("experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json")
    assert adjudication["primary_category"] == "v0708_external_validation_evidence_gap_no_candidate_opened"
    assert adjudication["candidate_identity_frozen"] is False
    assert adjudication["direction_scoring_opened"] is False
    assert (ROOT / "experiments/two_wave_external_validation_availability_v0708/RESULT_CARD.md").is_file()
    assert (ROOT / "docs/research/TWO_WAVE_EXTERNAL_VALIDATION_EVIDENCE_AVAILABILITY_V0708.md").is_file()
