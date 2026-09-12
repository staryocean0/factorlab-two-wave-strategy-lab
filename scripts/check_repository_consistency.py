#!/usr/bin/env python3
"""Read-only, fail-closed control-plane validation; no market scoring or network.

--write-docs regenerates only the six named current documents after validating
bound evidence. Historical protocols, data, source manifests and results are not
rewritten. A consistency pass is not a full Python 3.11 regression pass.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import posixpath
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = "experiments/two_wave_m0_authority.json"
LIFECYCLE = "docs/governance/REPOSITORY_LIFECYCLE.json"
ARCHIVE = "docs/archive/repository_consistency_20260912"
FALSE_FIELDS = (
    "morphology_acceptance", "trade_authority", "production_authority",
    "registered_use_authority", "fresh_oos", "candidate_identity_frozen",
    "external_validation_protocol_opened", "direction_scoring_opened",
    "threshold_change_opened", "result_opened", "temporal_trigger_A_satisfied",
    "independent_reference_trigger_B_satisfied",
)
CURRENT_DOCS = (
    "README.md", "docs/INDEX.md", "CONTINUE_HERE.md",
    "docs/research/TWO_WAVE_M0_AUTHORITY.md",
    "docs/research/TWO_WAVE_CURRENT_WHITEPAPER.md",
    "docs/research/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md",
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                       parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def safe_path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if not relative or path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError(f"unsafe repository path: {relative!r}")
    result = root.joinpath(*path.parts)
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path or symlink escaped repository: {relative}")
    return result


def git_blob_sha(content: bytes) -> str:
    prefix = f"blob {len(content)}\0".encode()
    return hashlib.sha1(prefix + content, usedforsecurity=False).hexdigest()


def pointer(value: Any, expression: str) -> Any:
    if not expression.startswith("/"):
        raise ValueError(f"expected absolute JSON pointer: {expression}")
    for token in expression[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_authority(a: dict[str, Any]) -> None:
    require(a.get("schema") == "two_wave_m0_authority@2.0", "unexpected current authority schema")
    require(a.get("scientific_version") == "v0.7.8", "scientific checkpoint changed without a maintenance migration")
    require(a.get("global_status") == "v0708_external_validation_evidence_gap_no_candidate_opened", "v0708 status drift")
    require(a.get("primary_object") == "two_wave_parent_structure_recognizer", "primary object drift")
    for key in FALSE_FIELDS:
        require(a.get(key) is False, f"must be explicit false, not missing/truthy: {key}")
    for key in ("direction_winner", "active_semantic_parent_authority"):
        require(key in a and a[key] is None, f"authority must remain explicitly null: {key}")
    c = a["component_authority"]
    require(c["parent_direction"]["winner"] is None, "component direction winner drift")
    require(c["semantic_parent"]["authority"] is None, "component parent authority drift")
    require(c["semantic_parent"]["observed_is_certified"] is False, "observation became certification")
    require(c["qualification"]["authority"] is None, "qualification authority drift")
    for key in ("v0647_temporal_replication_binding", "v0648_independent_reference_calibration_binding"):
        require(a["external_constraints"].get(key) is True, f"external negative evidence is no longer binding: {key}")
    e = a["execution_policy"]
    require(e.get("github_actions_quota_available") is False, "Actions quota status changed")
    require(e.get("github_actions_automatic_dispatch_authorized") is False, "automatic Actions execution enabled")
    require(e.get("new_experiment_authorized") is False, "cleanup cannot authorize a scientific experiment")
    m = a["metrics"]
    require(all(type(v) is int and v >= 0 for v in m.values()), "metric counts must be nonnegative integers")
    require(m["certified_publications"] + m["unresolved_publications"] == m["lifecycle_publications"], "lifecycle count identity failed")
    require(m["D1_uncertain_publications"] - m["v0625_uncertain_publications"] == m["v0625_uncertainty_rescues"], "rescue count identity failed")
    require(m["supported_case_denominator"] == m["qualified_semantic_supported_cases"], "case denominator drift")
    require(m["D1_supported_case_exact"] == m["v0625_supported_case_exact"], "v0707 semantic neutrality changed")
    require(m["D1_supported_publication_exact"] == m["v0625_supported_publication_exact"], "publication semantic neutrality changed")
    require(m["D1_evaluated_publications"] == m["v0625_evaluated_publications"] == m["v0618_qualified_publications"], "direction evaluation universe drift")


def validate_bindings(root: Path, a: dict[str, Any]) -> int:
    cache: dict[str, Any] = {}
    seen: set[str] = set()
    for binding in a["evidence_bindings"]:
        target = binding["target"]
        require(target not in seen, f"duplicate evidence binding: {target}")
        seen.add(target)
        source = binding["source"]
        if source not in cache:
            cache[source] = load_json(safe_path(root, source))
        actual = pointer(a, target)
        expected = pointer(cache[source], binding["pointer"])
        require(type(actual) is type(expected) and actual == expected, f"evidence mismatch: {target} <- {source}{binding['pointer']}")
    required = {"/metrics/" + key for key in a["metrics"]} | {"/global_status", "/next_authorized_step"}
    require(required <= seen, f"unbound current values: {sorted(required - seen)}")
    return len(seen)


def link(source: str, target: str, label: str | None = None) -> str:
    relative = posixpath.relpath(target, posixpath.dirname(source) or ".")
    return f"[{label or target}]({relative})"


def render_current_documents(a: dict[str, Any]) -> dict[str, str]:
    """One authored source for every active scientific status surface."""
    validate_authority(a)
    m = a["metrics"]
    def head(path: str, title: str) -> str:
        return (f"# {title}\n\n<!-- Generated by scripts/check_repository_consistency.py; do not hand-edit. -->\n\n"
                f"Scientific checkpoint: **{a['scientific_version']}**. Maintenance is not a new experiment.\n\n"
                f"Current status: `{a['global_status']}`.\n\n"
                f"Machine authority: {link(path, AUTHORITY)}. "
                "Active semantic-parent authority and direction winner are **null**. "
                "Morphology acceptance, trade, production, registered-use and fresh-OOS authority are **false**.\n\n")
    def findings() -> str:
        return ("| Component | Evidence and current role |\n| --- | --- |\n"
                f"| TCSS/extrema/ridge support | {m['ridge_supported_cases']}/{m['anchored_development_cases']} support; retain infrastructure, not semantic-parent authority. |\n"
                f"| Legacy exact consecutive five-ridge tuple | {m['legacy_exact_tuple_supported_cases']}/{m['anchored_development_cases']}; first major semantic break. Retained for historical replay, not current parent authority. |\n"
                f"| F3 lifecycle | {m['F3_lifecycle_live_supported_cases']}/{m['anchored_development_cases']} live support; C1-certified {m['F3_C1_certified_supported_cases']}/{m['anchored_development_cases']}. Observation is not certification. |\n"
                f"| Immutable raw publication | {m['lifecycle_publications']} publications: {m['certified_publications']} certified and {m['unresolved_publications']} unresolved. Development transplant supported. |\n"
                f"| v0.6.18 qualification on lifecycle publications | {m['v0618_qualified_publications']} qualified versus v0.5.4 control {m['v054_qualified_publications']}; semantic support {m['qualified_semantic_supported_cases']}/{m['anchored_development_cases']}. No independent qualification authority. |\n"
                f"| D1 / v0.6.25 direction transplant | Both evaluated {m['v0618_qualified_publications']} publications. v0.6.25 rescued {m['v0625_uncertainty_rescues']} uncertain publications, but both are exact on {m['D1_supported_case_exact']}/{m['supported_case_denominator']} supported cases and {m['D1_supported_publication_exact']}/{m['supported_publication_denominator']} supported publications. No semantic advantage or winner. |\n")
    def next_section(path: str) -> str:
        return ("## Current next step\n\n" + a["next_authorized_step"] + ".\n\n"
                "Both external prerequisites are currently unsatisfied. An older-period sample is not automatically fresh, "
                "and a duplicate DataHub export is not independent evidence. No in-sample rescue, threshold tuning, "
                "new direction scoring or production promotion is authorized. Documentation and integrity maintenance may continue.\n\n"
                f"Evidence: {link(path, a['evidence']['v0708_adjudication'])}.\n")
    def negatives() -> str:
        return (f"The retained v0.6.47 temporal replication has D1 exact {m['v0647_D1_exact']}/{m['v0647_pair_count']} "
                f"versus v0.6.25 {m['v0647_v0625_exact']}/{m['v0647_pair_count']}. "
                f"v0.6.48 independently confirmed only {m['v0648_reference_confirmed_candidates']}/{m['v0648_candidate_cases']} candidate parents, "
                f"with both directions exact on {m['v0648_D1_exact']}/{m['v0648_reference_confirmed_candidates']}. "
                "These are different evaluation universes from the selected Development salvage cases and remain binding negative evidence.\n")
    out: dict[str, str] = {}
    p = "README.md"
    out[p] = head(p, "FactorLab Two-Wave research") + (
        "## Purpose\n\nCausally identify two complete same-scale waves and classify their parent as "
        "**Range / UpTrend / DownTrend / Uncertain**. This repository studies structure/state recognition, not "
        "reversal-strategy PnL, risk-state switching, contract selection or live execution.\n\n"
        f"Start at {link(p, 'CONTINUE_HERE.md')}, {link(p, 'docs/INDEX.md')}, and "
        f"{link(p, 'docs/research/TWO_WAVE_CURRENT_WHITEPAPER.md', 'current whitepaper')}.\n\n"
        "## Current evidence\n\n" + findings() + "\n" + negatives() + "\n" + next_section(p) +
        "\n## Verification and history\n\n"
        "Run `python scripts/verify_repository.py --report /tmp/two-wave-verification.json` in a complete Python 3.11 checkout. "
        "Actions are not automatically dispatched while quota is unavailable. A new local full-suite receipt is still required "
        "for this maintenance revision; old green runs do not certify new changes.\n\n"
        f"Lifecycle and archive policy: {link(p, LIFECYCLE)}. "
        "Imported `ai-readme.md`, `docs/00-index.md`, old handoff prompts and versioned protocols are historical references, "
        "not competing current instructions. Frozen data/source hashes are retained.\n")
    p = "CONTINUE_HERE.md"
    out[p] = head(p, "Continue here") + (
        "v0.7.0-v0.7.7 are closed. v0.7.8 is a completed evidence-availability audit, not an experiment awaiting computation. "
        "Do not rerun salvage, qualification retries, direction transplantation or an old governance one-shot just to continue.\n\n"
        + next_section(p) + "\n## Maintenance verification handoff\n\n"
        "Task **TW-CONSISTENCY-20260912-01** requires a complete Python 3.11 checkout for source/data validation and full pytest. "
        "Current-session checks and historical green CI are not substitutes for that receipt. "
        f"Use {link(p, 'docs/ops/cloud_local_communication.md')} and {link(p, 'docs/ops/CURRENT_WORKFLOW.md')}.\n\n"
        "Do not use Actions while quota is unavailable. Do not manufacture reference labels, fresh-OOS status or a winner. "
        "The old v0.7.7 governance CLI now fails closed; its import-only API is retained solely for historical regression tests.\n")
    p = "docs/research/TWO_WAVE_M0_AUTHORITY.md"
    out[p] = head(p, "Two-Wave M0 current authority") + (
        "M0 schema 2.0 separates current status from historical detail. The v1.32 payload is preserved byte-for-byte at "
        + link(p, a["history"]["snapshot"]) + ". It is evidence, not a second current authority. "
        "The historical full-recognizer operational baseline remains v0.4.3 until complete morphology acceptance; "
        "no component transplant silently replaces it.\n\n" + findings() + "\n## Binding limits\n\n" + negatives() +
        "\n" + next_section(p) + "\n## Synchronization contract\n\n"
        "Every displayed count and reopening condition is bound to a frozen adjudication or the pinned historical authority snapshot. "
        "The consistency checker rejects missing/changed evidence, unbound metrics, divergent generated documents and authority escalation.\n")
    p = "docs/research/TWO_WAVE_CURRENT_WHITEPAPER.md"
    out[p] = head(p, "Two-Wave current whitepaper") + (
        "## 1. Research object and non-goals\n\n"
        "A parent consists of two complete same-scale waves with five ordered semantic anchors. The target is its present "
        "structural state, including an explicit Uncertain state. Recognition is not a forecast of the next wave and is not a trading policy. "
        "Index prices provide a signal surface, not executable IM, ETF or option fills.\n\n"
        "## 2. What the salvage staircase established\n\n" + findings() +
        "\nThe sharp loss occurs when ridge-supported human anchors are forced into a consecutive exact tuple. "
        "Retaining the ridge machinery therefore does not authorize the old objectization. F3 is the separately frozen "
        "persistence-dominant nonconsecutive quintet reconstruction, not a fitted distance tolerance or a post-hoc relaxation of the old tuple.\n\n"
        "## 3. Causal lifecycle and immutable publication\n\n"
        "The static F3 object and a permanent event certificate are different objects of evidence. v0.7.2-v0.7.3 showed "
        "that explicit skipped-ridge death proof may arrive after the cutoff. v0.7.4 consequently records first observation "
        "and later status transitions append-only. Live unresolved objects remain explicitly unresolved; future certification "
        "must not be backdated. Event time, observation time, certificate time and publication time must remain distinct.\n\n"
        "v0.7.5 applies sequential raw projection and first-valid publication to the observed lifecycle. The first published "
        "raw identity cannot be rewritten by later evidence. v0.7.6 transplants qualification without changing its thresholds "
        "or conditioning on final/future lifecycle state. v0.7.7 evaluates D1 and v0.6.25 only on that immutable qualified universe.\n\n"
        "## 4. Interpretation and external validity\n\n" + negatives() +
        "\nEleven selected anchored Development cases cannot establish population-wide morphology precision. "
        "The 115-publication direction universe, nine supported cases and eleven supported publications must not be mixed. "
        "The nineteen uncertainty rescues measure mechanical expression, not proven human-semantic improvement. "
        "Neither a CI pass nor source transport creates scientific evidence.\n\n"
        "## 5. Data and implementation boundary\n\n"
        "Shipped data remain CSI1000 2015-01-05 through 2020-12-31 Development material. "
        "The original source closure, data files and scientific library trees remain frozen. "
        "The closed v0.6.47 external-clock/resampling protocol was a scoped validation exception, not a current blanket permission. "
        "No new external scoring or raw-data import is opened by this maintenance.\n\n"
        "Scientific libraries remain under `src/factor_lab/visual_structure/` and `src/factor_lab/market_state/`; "
        "shared imported dependencies remain under `shared/`. Historical runners are preserved because later adapters/tests "
        "may import them. For historical qualification replay, the v0.7.6 retry adapter is the authoritative adapter, not its "
        "invalid first-run serialization path; v0.7.7 uses its formal adapter. Their presence is not permission to rerun outcomes.\n\n"
        "## 6. Verification and document lifecycle\n\n"
        + link(p, "docs/ops/CURRENT_WORKFLOW.md", "Current verification workflow") + " specifies the shared entrypoint. "
        "Consistency checks validate bindings, current links, archived bytes, immutable source policy, protected code/data trees, "
        "Python syntax and workflow opt-in boundaries. Source/data validation and the full Python 3.11 test suite remain separate "
        "required checks. The imported four-layer whitepapers define infrastructure contracts only; they do not replace this current "
        "scientific whitepaper. Versioned research protocols and negative results retain their original wording and hashes.\n\n"
        + next_section(p))
    p = "docs/research/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md"
    out[p] = head(p, "Two-Wave direction contribution ledger — current view") + (
        "## Retained contribution, not winner\n\n"
        "D1 is the historical baseline. v0.6.25 remains a non-winning Development contribution. "
        f"The v0.7.7 transplant evaluated {m['v0618_qualified_publications']} immutable qualified publications and rescued "
        f"{m['v0625_uncertainty_rescues']} D1-uncertain publications; the supported semantic subset remains tied at "
        f"{m['D1_supported_case_exact']}/{m['supported_case_denominator']} cases and "
        f"{m['D1_supported_publication_exact']}/{m['supported_publication_denominator']} publications.\n\n" + negatives() +
        "\n## Closed families remain closed\n\n"
        "Endpoint D2/confidence-gated D2, PAWCT, the in-sample Range/W1/residual families, native high/low, and native open/body/gap "
        "must not be repackaged as new direction experiments. Earlier contributions and negative results remain in the "
        + link(p, ARCHIVE + "/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md", "byte-preserved historical ledger") +
        " and their versioned protocols/adjudications. Historical next-step language there is not current authorization.\n\n"
        + next_section(p))
    p = "docs/INDEX.md"
    out[p] = head(p, "Two-Wave current document index") + (
        "## Current control plane\n\n" + "\n".join(
            "- " + link(p, target) for target in (
                "CONTINUE_HERE.md", "AGENTS.md", "docs/research/TWO_WAVE_M0_AUTHORITY.md",
                "docs/research/TWO_WAVE_CURRENT_WHITEPAPER.md", "docs/research/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md",
                LIFECYCLE, "docs/ops/CURRENT_WORKFLOW.md", "docs/ops/cloud_local_communication.md",
                "docs/ops/REPOSITORY_CONSISTENCY_AUDIT_20260912.md")) +
        "\n\n## Latest closed evidence\n\n" + "\n".join("- " + link(p, target) for target in (
            a["evidence"]["v0707_adjudication"], a["evidence"]["v0708_adjudication"],
            "docs/research/TWO_WAVE_EXTERNAL_VALIDATION_EVIDENCE_AVAILABILITY_V0708.md")) +
        "\n\n## Frozen infrastructure dependencies — not separate current research mandates\n\n" +
        "\n".join("- " + link(p, target) for target in (
            "docs/ops/timing_infrastructure_four_layer_inventory@1.0.json",
            "docs/ops/timing_infrastructure_four_layer_split_whitepaper.md",
            "docs/ops/timing_layer2_measurement_plane@2.3.json",
            "docs/ops/timing_layer3_strategy_architecture@2.2.json",
            "docs/ops/timing_strategy_identity_registry@2.2.json",
            "docs/governance/data_usage_declaration.json", "docs/governance/layer3_tool16_candidate_slot.json",
            "docs/governance/source_closure_manifest.json", "data/manifest.json")) +
        "\n\n## Historical/reference material\n\n"
        "Versioned `docs/research/*PROTOCOL.md`, experiment folders, imported `docs/user/`, `docs/reference/`, "
        "`docs/00-index.md` and `ai-readme.md` are retained historical specifications/evidence, not current startup instructions. "
        "Older whitepapers remain immutable infrastructure references. The migrated v1-v13 recognizer archive is comparison "
        "material, not a Two-Wave winner. No historical outcome file is deleted or rewritten by the cleanup.\n\n"
        + link(p, ARCHIVE + "/ARCHIVE_NOTE.md", "Superseded control-plane snapshots") + " explains original paths and byte preservation.\n\n"
        + next_section(p))
    require(set(out) == set(CURRENT_DOCS), "generated document allowlist drift")
    return out


def validate_links(root: Path, source: str, text: str) -> int:
    count = 0
    for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", text):
        if "://" in target or target.startswith(("mailto:", "#")):
            continue
        target = target.split("#", 1)[0]
        relative = posixpath.normpath(posixpath.join(posixpath.dirname(source), target))
        require(safe_path(root, relative).exists(), f"broken current link: {source} -> {target}")
        count += 1
    return count


def classify_path(path: str, life: dict[str, Any], seed_paths: set[str]) -> str:
    if path == AUTHORITY:
        return "current_machine_authority"
    if path in life["generated_current_documents"] or path == "AGENTS.md":
        return "current_control_document"
    if path in life["active_validation_entrypoints"]:
        return "active_validation_code"
    if path in life["retired_write_entrypoints"]:
        return "retired_cli_historical_import_compatibility"
    if path in life["allowed_workflows"]:
        return "manual_opt_in_verification_recipe"
    if path.startswith("docs/archive/"):
        return "archived_evidence_not_current_authority"
    if path in life["imported_noncurrent_entrypoints"]:
        return "frozen_imported_noncurrent_entrypoint"
    if path.startswith("tests/"):
        return "active_regression_test"
    if path in seed_paths:
        return "frozen_imported_dependency_or_reference"
    if path in life["allowed_root_files"]:
        return "package_configuration"
    for prefix, role in life["historical_tree_roles"].items():
        if path.startswith(prefix):
            return role
    raise ValueError(f"unclassified repository component: {path}")


def validate_workflow_text(text: str) -> None:
    # Deliberately accept only the simple audited event-block style, rather than
    # pretending a regular expression is a general YAML parser.
    blocks = re.findall(r"(?ms)^on:\n(.*?)(?=^\S|\Z)", text)
    require(len(blocks) == 1, "expected one explicit on: block")
    event_lines = [line for line in blocks[0].splitlines()
                   if line.startswith("  ") and not line.startswith("    ")
                   and line.strip() and not line.lstrip().startswith("#")]
    require(event_lines == ["  workflow_dispatch:"], "only manual workflow_dispatch is allowed")
    require("        default: false" in blocks[0], "manual confirmation must default false")
    require("vars.TWO_WAVE_ACTIONS_ALLOWED == 'true'" in text
            and "inputs.confirm_quota_and_authorization" in text, "workflow authorization gate missing")
    require("  contents: read" in text and "contents: write" not in text, "workflow must not write repository contents")
    require("python scripts/verify_repository.py" in text, "CI and local verification entrypoints differ")


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if proc.returncode:
        raise ValueError(f"complete Git checkout required: git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def validate_repository(root: Path) -> dict[str, Any]:
    a = load_json(root / AUTHORITY)
    life = load_json(root / LIFECYCLE)
    validate_authority(a)
    require(life["machine_authority"] == AUTHORITY, "competing machine authority")
    require(set(life["generated_current_documents"]) == set(CURRENT_DOCS), "current document allowlist mismatch")
    pins_checked = 0
    for entry in life["archive_snapshots"]:
        data = safe_path(root, entry["archive_path"]).read_bytes()
        require(git_blob_sha(data) == entry["git_blob_sha"], f"archived bytes drifted: {entry['archive_path']}")
        pins_checked += 1
    for path, expected in life.get("evidence_pins", {}).items():
        require(git_blob_sha(safe_path(root, path).read_bytes()) == expected, f"adjudication bytes drifted: {path}")
        pins_checked += 1
    manifest_path = safe_path(root, life["frozen_source_manifest"])
    require(git_blob_sha(manifest_path.read_bytes()) == life["frozen_source_manifest_git_blob_sha"], "source-closure manifest was rewritten")
    require(life["frozen_source_relocations"] == {".github/workflows/ci.yml": ARCHIVE + "/ci.yml"}, "unapproved source relocation")
    require(hashlib.sha256((root / ARCHIVE / "ci.yml").read_bytes()).hexdigest() == life["workflow_original_sha256"], "original CI source closure lost")
    bindings_checked = validate_bindings(root, a)
    links_checked = 0
    for path, expected in render_current_documents(a).items():
        actual = safe_path(root, path).read_text(encoding="utf-8")
        require(actual == expected, f"current document drift: {path}; regenerate rather than appending status")
        links_checked += validate_links(root, path, actual)
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    require(AUTHORITY in agents and "CONTINUE_HERE.md" in agents and a["scientific_version"] in agents, "AGENTS startup authority drift")
    expected_workflows = set(life["allowed_workflows"])
    actual_workflows = {p.relative_to(root).as_posix() for p in (root / ".github/workflows").glob("*") if p.is_file()}
    require(actual_workflows == expected_workflows, "unexpected/one-shot workflow present")
    wf = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    validate_workflow_text(wf)
    require(git_blob_sha(wf.encode()) == life["current_workflow_git_blob_sha"], "current verification recipe drift")
    for path, detail in life["retired_write_entrypoints"].items():
        require(git_blob_sha((root / path).read_bytes()) == detail["compatibility_stub_git_blob_sha"], f"retired writer guard changed: {path}")
    seed_paths = {entry["path"] for entry in load_json(manifest_path)["files"]}
    tracked = [p for p in _git(root, "ls-files", "-z").split("\0") if p]
    require(bool(tracked), "empty tracked inventory")
    inventory = []
    syntax_checked = 0
    for path in tracked:
        item = safe_path(root, path)
        require(item.is_file(), f"tracked file missing: {path}")
        role = classify_path(path, life, seed_paths)
        inventory.append({"path": path, "role": role})
        if path.endswith(".py"):
            ast.parse(item.read_text(encoding="utf-8-sig"), filename=path)
            syntax_checked += 1
        if path.endswith(".sh"):
            check = subprocess.run(["bash", "-n", str(item)], capture_output=True, text=True, check=False)
            require(check.returncode == 0, f"shell syntax failed: {path}: {check.stderr}")
    for path, expected in life["protected_base_trees"].items():
        require(_git(root, "rev-parse", f"HEAD:{path}").strip() == expected, f"protected scientific/data tree changed: {path}")
        require(not _git(root, "status", "--porcelain", "--untracked-files=all", "--", path).strip(), f"uncommitted protected tree change: {path}")
    return {"schema": "two_wave_repository_consistency_receipt@1.0", "status": "passed_static_consistency_only",
            "scientific_version": a["scientific_version"], "git_head": _git(root, "rev-parse", "HEAD").strip(),
            "archive_and_evidence_pins_checked": pins_checked, "evidence_bindings_checked": bindings_checked,
            "current_links_checked": links_checked, "python_files_syntax_checked": syntax_checked,
            "tracked_component_count": len(inventory), "inventory": inventory,
            "full_regression_executed": False, "market_scoring_executed": False, "authority_granted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write-docs", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        if args.write_docs:
            a = load_json(args.root / AUTHORITY)
            validate_authority(a)
            validate_bindings(args.root, a)
            for path, text in render_current_documents(a).items():
                destination = safe_path(args.root, path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(text, encoding="utf-8")
        result = validate_repository(args.root)
    except (ValueError, KeyError, IndexError, OSError, SyntaxError) as exc:
        result = {"schema": "two_wave_repository_consistency_receipt@1.0", "status": "failed",
                  "error": str(exc), "full_regression_executed": False, "authority_granted": False}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "passed_static_consistency_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
