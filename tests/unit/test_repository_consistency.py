"""Maintenance regressions. Synthetic fixtures test guards, not market outcomes."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = _module("_repository_consistency", ROOT / "scripts/check_repository_consistency.py")
RUNNER = _module("_verification_runner", ROOT / "scripts/verify_repository.py")


def _authority():
    return CHECK.load_json(ROOT / CHECK.AUTHORITY)


def test_current_authority_is_blocked_and_internally_consistent():
    CHECK.validate_authority(_authority())


@pytest.mark.parametrize("field", CHECK.FALSE_FIELDS)
@pytest.mark.parametrize("bad_value", [True, 0, "false", None])
def test_false_authority_fields_reject_escalation_missing_and_wrong_type(field, bad_value):
    a = _authority()
    a[field] = bad_value
    with pytest.raises(ValueError):
        CHECK.validate_authority(a)


@pytest.mark.parametrize("field", ["direction_winner", "active_semantic_parent_authority"])
def test_null_authorities_reject_missing_or_winner(field):
    a = _authority()
    a.pop(field)
    with pytest.raises(ValueError):
        CHECK.validate_authority(a)
    a[field] = "winner"
    with pytest.raises(ValueError):
        CHECK.validate_authority(a)


def test_certificate_is_not_first_observation():
    a = _authority()
    a["component_authority"]["semantic_parent"]["observed_is_certified"] = True
    with pytest.raises(ValueError):
        CHECK.validate_authority(a)


def test_case_and_publication_denominators_are_not_interchangeable():
    a = _authority()
    a["metrics"]["supported_case_denominator"] = 11
    with pytest.raises(ValueError):
        CHECK.validate_authority(a)


def test_rescue_supply_is_not_semantic_advantage():
    a = _authority()
    a["metrics"]["v0625_supported_case_exact"] = 8
    with pytest.raises(ValueError):
        CHECK.validate_authority(a)


def test_duplicate_and_nonfinite_json_fail_closed(tmp_path):
    p = tmp_path / "x.json"
    for text in ('{"winner":null,"winner":"D1"}', '{"x":NaN}', '[]'):
        p.write_text(text)
        with pytest.raises(ValueError):
            CHECK.load_json(p)


@pytest.mark.parametrize("relative", ["../outside", "/tmp/escape", "a/../../escape", "a\\escape", ""])
def test_paths_cannot_escape_the_repository(tmp_path, relative):
    with pytest.raises(ValueError):
        CHECK.safe_path(tmp_path, relative)


def test_symlink_escape_rejected(tmp_path):
    (tmp_path / "outside").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        CHECK.safe_path(tmp_path, "outside/escape")


def test_json_pointer_escaping_and_list_index():
    assert CHECK.pointer({"a/b": {"~": [17]}}, "/a~1b/~0/0") == 17
    with pytest.raises(ValueError):
        CHECK.pointer({}, "not-absolute")


def _put_nested(root, pointer, value):
    parts = pointer.lstrip("/").split("/")
    for part in parts[:-1]:
        root = root.setdefault(part, {})
    root[parts[-1]] = copy.deepcopy(value)


def _binding_fixture(tmp_path, a):
    """Deliberately synthetic evidence for unit-testing comparison mechanics."""
    sources = {}
    for binding in a["evidence_bindings"]:
        obj = sources.setdefault(binding["source"], {})
        _put_nested(obj, binding["pointer"], CHECK.pointer(a, binding["target"]))
    for path, obj in sources.items():
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(obj))


def test_evidence_binding_equality_and_mismatch(tmp_path):
    a = _authority()
    _binding_fixture(tmp_path, a)
    assert CHECK.validate_bindings(tmp_path, a) == len(a["evidence_bindings"])
    a["metrics"]["ridge_supported_cases"] += 1
    with pytest.raises(ValueError, match="evidence mismatch"):
        CHECK.validate_bindings(tmp_path, a)


def test_binding_cannot_be_omitted_or_duplicated(tmp_path):
    a = _authority()
    _binding_fixture(tmp_path, a)
    original = copy.deepcopy(a)
    a["evidence_bindings"].pop(0)
    with pytest.raises(ValueError, match="unbound"):
        CHECK.validate_bindings(tmp_path, a)
    a = original
    a["evidence_bindings"].append(a["evidence_bindings"][0])
    with pytest.raises(ValueError, match="duplicate evidence"):
        CHECK.validate_bindings(tmp_path, a)


def test_all_current_documents_equal_the_complete_rendering():
    rendered = CHECK.render_current_documents(_authority())
    assert set(rendered) == set(CHECK.CURRENT_DOCS)
    for path, text in rendered.items():
        assert (ROOT / path).read_text() == text
        assert text.count("Current status:") == 1


def test_current_link_checker_rejects_a_missing_target(tmp_path):
    (tmp_path / "ok.md").write_text("ok")
    assert CHECK.validate_links(tmp_path, "README.md", "[ok](ok.md)") == 1
    with pytest.raises(ValueError, match="broken current link"):
        CHECK.validate_links(tmp_path, "README.md", "[bad](missing.md)")


def test_component_roles_do_not_promote_old_entrypoints_or_delete_base_adapters():
    life = CHECK.load_json(ROOT / CHECK.LIFECYCLE)
    assert CHECK.classify_path("ai-readme.md", life, {"ai-readme.md"}) == "frozen_imported_noncurrent_entrypoint"
    assert CHECK.classify_path(CHECK.AUTHORITY, life, set()) == "current_machine_authority"
    assert CHECK.classify_path("scripts/close_two_wave_v0707_governance.py", life, set()) == "retired_cli_historical_import_compatibility"
    assert "historical_replay" in CHECK.classify_path("scripts/run_two_wave_f3_lifecycle_qualification_transplant_v0706.py", life, set())
    assert CHECK.classify_path("tests/unit/test_old.py", life, set()) == "active_regression_test"
    with pytest.raises(ValueError, match="unclassified"):
        CHECK.classify_path("unregistered_new_authority.json", life, set())


def test_manual_workflow_matches_its_pin_and_shared_runner():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    life = CHECK.load_json(ROOT / CHECK.LIFECYCLE)
    CHECK.validate_workflow_text(text)
    assert CHECK.git_blob_sha(text.encode()) == life["current_workflow_git_blob_sha"]


@pytest.mark.parametrize("event", ["push", "pull_request", "schedule", "workflow_run", '"push"'])
def test_workflow_automatic_and_quoted_triggers_rejected(event):
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    text = text.replace("on:\n", f"on:\n  {event}:\n")
    with pytest.raises(ValueError):
        CHECK.validate_workflow_text(text)


def test_workflow_quota_confirmation_cannot_default_true():
    text = (ROOT / ".github/workflows/ci.yml").read_text().replace("default: false", "default: true")
    with pytest.raises(ValueError):
        CHECK.validate_workflow_text(text)


def test_retired_cli_exits_without_touching_current_authority(tmp_path):
    before = (ROOT / CHECK.AUTHORITY).read_bytes()
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/close_two_wave_v0707_governance.py")], cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 2
    assert "RETIRED" in proc.stderr
    assert (ROOT / CHECK.AUTHORITY).read_bytes() == before


def test_shared_runner_has_no_scientific_outcome_command():
    assert RUNNER.verification_commands("python", False) == [
        ["python", "scripts/check_repository_consistency.py"],
        ["python", "scripts/validate_theme_package.py"],
        ["python", "-m", "pytest", "-q"],
    ]
    assert len(RUNNER.verification_commands("python", True)) == 1


def _source_validator_core():
    """Load only stdlib source-hash functions; no fake numpy/pyarrow module stubs."""
    tree = ast.parse((ROOT / "scripts/validate_theme_package.py").read_text())
    names = {"_sha256", "_require_json", "validate_source_closure"}
    keep = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    ns = {"hashlib": hashlib, "json": json, "Path": Path}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "source_validator_core", "exec"), ns)
    return ns


def _source_fixture(tmp_path):
    source = _source_validator_core()
    source.update(ROOT=tmp_path, SOURCE_MANIFEST=tmp_path / "manifest.json",
                  MUTABLE_AUTHORITY_PATHS={"AGENTS.md", "README.md", "docs/INDEX.md", "scripts/validate_theme_package.py"},
                  FROZEN_SOURCE_RELOCATIONS={".github/workflows/ci.yml": CHECK.ARCHIVE + "/ci.yml"})
    files = []
    for p in source["MUTABLE_AUTHORITY_PATHS"]:
        path = tmp_path / p; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("mutable")
        files.append({"path": p, "sha256": "historical-not-compared"})
    for p, text in [(".github/workflows/ci.yml", "original CI"), ("src/frozen.py", "frozen source")]:
        dest = tmp_path / source["FROZEN_SOURCE_RELOCATIONS"].get(p, p)
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(text)
        files.append({"path": p, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    current = tmp_path / ".github/workflows/ci.yml"
    current.parent.mkdir(parents=True, exist_ok=True); current.write_text("manual replacement")
    source["SOURCE_MANIFEST"].write_text(json.dumps({"files": files}))
    return source


def test_relocated_frozen_workflow_still_checks_original_bytes(tmp_path):
    ns = _source_fixture(tmp_path)
    result = ns["validate_source_closure"]()
    assert result == {"source_files_checked": 2, "mutable_authority_files_checked": 4, "relocated_frozen_entries_checked": 1}
    (tmp_path / CHECK.ARCHIVE / "ci.yml").write_text("changed archive")
    with pytest.raises(RuntimeError, match="frozen source drifted"):
        ns["validate_source_closure"]()


def test_unrelated_frozen_source_is_not_exempted(tmp_path):
    ns = _source_fixture(tmp_path)
    (tmp_path / "src/frozen.py").write_text("changed source")
    with pytest.raises(RuntimeError, match="frozen source drifted"):
        ns["validate_source_closure"]()


def test_relocated_source_requires_current_replacement(tmp_path):
    ns = _source_fixture(tmp_path)
    (tmp_path / ".github/workflows/ci.yml").unlink()
    with pytest.raises(RuntimeError, match="current replacement missing"):
        ns["validate_source_closure"]()
