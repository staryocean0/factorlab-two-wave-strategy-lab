import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "close_two_wave_v0707_governance.py"
SPEC = importlib.util.spec_from_file_location("close_two_wave_v0707_governance", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
GOVERNANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GOVERNANCE)

ADJUDICATION_PATH = GOVERNANCE.ADJUDICATION_PATH
AUTHORITY_PATH = GOVERNANCE.AUTHORITY_PATH
EXPECTED_CATEGORY = GOVERNANCE.EXPECTED_CATEGORY
RESULT_PATH = GOVERNANCE.RESULT_PATH
updated_authority = GOVERNANCE.updated_authority
verify_formal_result = GOVERNANCE.verify_formal_result


def _load(path: Path):
    return json.loads(path.read_text())


def test_formal_v0707_result_and_adjudication_are_governance_compatible():
    result = _load(RESULT_PATH)
    adjudication = _load(ADJUDICATION_PATH)
    verify_formal_result(result, adjudication)
    assert result["primary_category"] == EXPECTED_CATEGORY


def test_authority_update_keeps_all_runtime_authority_off():
    result = _load(RESULT_PATH)
    authority = updated_authority(_load(AUTHORITY_PATH), result)
    assert authority["schema"] == "two_wave_m0_authority@1.32"
    assert authority["component_authority"]["parent_direction"]["winner"] is None
    assert authority["no_current_direction_challenger_authorized"] is True
    v0707 = authority["f3_lifecycle_direction_transplant"]["v0707"]
    assert v0707["v0625_rescue_count"] == 19
    assert v0707["D1_case_exact_count"] == v0707["v0625_case_exact_count"] == 7
    assert v0707["v0625_semantic_advantage_over_D1"] is False
    assert v0707["v0647_external_validation_weakness_binding"] is True
    assert v0707["v0648_external_validation_weakness_binding"] is True
    assert v0707["direction_winner_installed"] is False
    assert v0707["active_parent_authority_granted"] is False
    assert v0707["trade_authority_changed"] is False
    assert v0707["production_authority_changed"] is False
