#!/usr/bin/env python3
"""One-time, pinned repository reconciliation. No scientific computation.

Run from the repository root. Existing base files must still equal the frozen
input tree. A preservation manifest makes reapplication fail closed.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

BASE = 'ec0d49f1cec7d6c34d13af0fcfdb824687d57392'
TREE = '9679ee00f5aa063b2208e597e590d1a70edaa917'
MANIFEST = 'docs/governance/repository_preservation_manifest_20260912.json'
CONTROL = {
    'README.md', 'AGENTS.md', 'docs/INDEX.md', 'data/README.md',
    'docs/research/TWO_WAVE_M0_AUTHORITY.md',
    'docs/research/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md',
    'experiments/two_wave_m0_authority.json',
    'docs/governance/package_scope.json',
    'docs/governance/data_usage_declaration.json',
    'docs/governance/controller_validation.json',
    'scripts/validate_theme_package.py', 'scripts/close_two_wave_v0707_governance.py',
    '.codex/CLOUD_ENVIRONMENT.md', '.codex/cloud_verify.sh', '.github/workflows/ci.yml',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', required=True)
    parser.add_argument('--source-ref', default=BASE)
    args = parser.parse_args()
    root = Path.cwd()
    if (root/MANIFEST).exists():
        raise SystemExit('Already reconciled: do not replay an old governance migration.')
    actual_tree = subprocess.check_output(['git', 'rev-parse', args.source_ref+'^{tree}'], text=True).strip()
    if actual_tree != TREE:
        raise SystemExit(f'Input tree drift: {actual_tree} != {TREE}')
    raw = subprocess.check_output(['git', 'ls-tree', '-r', '-z', args.source_ref])
    original = {}
    for item in raw.split(b'\0'):
        if not item:
            continue
        header, name = item.split(b'\t', 1)
        name = name.decode()
        blob = header.split()[2].decode()
        data = (root/name).read_bytes()
        actual = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if actual != blob:
            raise SystemExit(f'Concurrent/base-file change: {name}')
        original[name] = (data, blob)
    seed = {x['path'] for x in json.loads((root/'docs/governance/source_closure_manifest.json').read_text())['files']}
    entries, dedup, redirects, removed, copies = [], {}, 0, 0, 0
    for name, (data, blob) in sorted(original.items()):
        sha = hashlib.sha256(data).hexdigest()
        snapshot_doc = name in seed and name.endswith('.md') and name not in CONTROL
        retired_skill = name.startswith('.codex/skills/')
        if snapshot_doc or retired_skill or name in CONTROL:
            prefix = 'archive/upstream_seed/' if snapshot_doc or retired_skill else 'archive/control_plane_20260912/'
            dest = dedup.get(sha, prefix+name)
            if sha not in dedup:
                path = root/dest
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                dedup[sha] = dest
                copies += 1
            if retired_skill:
                (root/name).unlink()
                disposition = 'archived_removed_active_path'
                removed += 1
            elif snapshot_doc:
                disposition = 'archived_with_redirect'
                redirects += 1
            else:
                disposition = 'maintained_with_original_archived'
        else:
            dest, disposition = name, 'retained_unchanged'
        entries.append({'original_path': name, 'preserved_path': dest, 'sha256': sha,
                        'git_blob_sha': blob, 'disposition': disposition})
    payload = {'schema': 'two_wave_repository_preservation@1.0', 'date': '2026-09-12',
               'base_commit': BASE, 'base_tree': TREE,
               'main_at_start': 'ef29291535bc0fc239269ee9cb7c8e5a8512418c',
               'original_file_count': len(entries), 'archive_copy_count': copies,
               'redirected_document_count': redirects, 'retired_auto_discovery_files': removed,
               'files': entries}
    (root/MANIFEST).write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    a_path = root/'experiments/two_wave_m0_authority.json'
    a = json.loads(a_path.read_text())
    e_path = 'experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json'
    e = json.loads((root/e_path).read_text())
    if e['primary_category'] != 'v0708_external_validation_evidence_gap_no_candidate_opened':
        raise SystemExit('Unexpected scientific adjudication; do not reinterpret it during maintenance.')
    a['schema'] = 'two_wave_m0_authority@1.33'
    a['current_scientific_revision'] = 'v0.7.8'
    a['global_status'] = e['primary_category']
    a['next_authorized_step'] = e['next_authorized_step']
    a['current_external_validation_availability_status'] = e['primary_category']
    p = a['component_authority']['parent_identity']
    p['historical_identity_version'] = p['version']
    p['historical_identity_name'] = p['name']
    p['version'] = 'v0.7.4'
    p['name'] = 'F3 prefix-causal lifecycle Development representation'
    retention = a['counteroffensive_component_retention']
    retention['tuple_birth_causal_adjacency_rule'] = 'v0702_v0703_certificate_gap_diagnosed_v0704_lifecycle_supported_development_only'
    retention['legacy_filtered_parent_identity'] = 'historical_exact_tuple_not_active_parent_authority_f3_lifecycle_development_reconstruction'
    retention['direction_D1_v0625'] = 'v0707_transplant_completed_development_contribution_no_winner_v0708_external_evidence_blocked'
    a['external_validation_availability'] = {'v0708': {
        'adjudication': e_path, 'audit_record': e['audit_record'],
        'connected_repository_count_at_audit': e['connected_repository_count'],
        'primary_category': e['primary_category'],
        **{k: e[k] for k in ('candidate_identity_frozen', 'external_validation_protocol_opened',
          'direction_scoring_opened', 'threshold_change_opened', 'result_opened',
          'temporal_trigger_A_satisfied', 'independent_reference_trigger_B_satisfied')},
    }}
    a['maintenance_reconciliation'] = {'date': '2026-09-12', 'scientific_experiment_opened': False,
                                     'original_preservation_manifest': MANIFEST}
    a_path.write_text(json.dumps(a, ensure_ascii=False, indent=2)+'\n')
    usage_path = root/'docs/governance/data_usage_declaration.json'
    u = json.loads(usage_path.read_text())
    u['schema_id'] = 'two_wave_cloud_theme_data_usage@1.1'
    u['declared_before_strategy_or_morphology_results'] = False
    u['record_role'] = 'current_scope_reconciliation_not_a_new_pre_result_data_declaration'
    u['original_pre_result_declaration'] = 'archive/control_plane_20260912/docs/governance/data_usage_declaration.json'
    u['physically_withheld_intervals'] = [{
        'start': '2021-01-01', 'end': '2026-08-21', 'role': 'not_shipped_in_current_working_tree',
        'reason': 'physical absence does not imply unconsumed evidence; v0647 consumed external 2024/2025/2026 material',
    }]
    u['external_replication_history'] = {
        'protocol': 'docs/research/TWO_WAVE_INDEPENDENT_TEMPORAL_MORPHOLOGY_REPLICATION_V0647_PROTOCOL.md',
        'consumed_years': [2024, 2025, 2026], 'last_consumed_day': '2026-08-21',
        'fresh_oos': False, 'new_download_authorized_by_this_maintenance': False,
        'validation_resampling_exception': 'frozen validation_resample_v0647 only; no general resampling authority',
    }
    usage_path.write_text(json.dumps(u, ensure_ascii=False, indent=2)+'\n')
    scope_path = root/'docs/governance/package_scope.json'
    s = json.loads(scope_path.read_text())
    s['schema_id'] = 'two_wave_cloud_theme_package_scope@1.1'
    s['package_role'] = 'bounded_two_wave_research_repository'
    s.pop('private_repository_required', None)
    s['repository_visibility_observed'] = 'public'
    s['visibility_changed_by_this_maintenance'] = False
    s['seed_privacy_statement'] = 'historical private requirement preserved in original scope; current repository is already public'
    s['current_authority'] = 'experiments/two_wave_m0_authority.json'
    s['scientific_revision'] = 'v0.7.8'
    scope_path.write_text(json.dumps(s, ensure_ascii=False, indent=2)+'\n')
    (root/'docs/governance/controller_validation.json').write_text(json.dumps({
        'schema_id': 'two_wave_validation_entrypoint@2.0',
        'record_role': 'current_validation_commands_not_a_static_success_certificate',
        'historical_seed_validation': 'archive/control_plane_20260912/docs/governance/controller_validation.json',
        'commands': ['python scripts/repository_consistency.py --check',
                     'python scripts/validate_theme_package.py', 'python -m pytest -q'],
        'required_python': '3.11', 'morphology_acceptance': False,
        'trade_authority': False, 'production_authority': False,
    }, ensure_ascii=False, indent=2)+'\n')
    vpath = root/'scripts/validate_theme_package.py'
    text = vpath.read_text()
    old = '    checked = 0\n    mutable_checked = 0\n'
    new = '''    preservation = _require_json(ROOT / "docs/governance/repository_preservation_manifest_20260912.json")
    locations = {row["original_path"]: row["preserved_path"] for row in preservation["files"]}
    checked = 0
    mutable_checked = 0
    archived_checked = 0
'''
    if text.count(old) != 1:
        raise SystemExit('Validator patch context mismatch')
    text = text.replace(old, new)
    old = '        if not path.is_file() or _sha256(path) != str(item["sha256"]):\n'
    new = '''        preserved = locations.get(relative, relative)
        if preserved != relative:
            destination = Path(preserved)
            if destination.is_absolute() or ".." in destination.parts or not preserved.startswith("archive/"):
                raise RuntimeError(f"unsafe source archive mapping: {relative}")
            path = ROOT / destination
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
                raise RuntimeError(f"source archive escaped repository: {relative}")
            archived_checked += 1
        if not path.is_file() or _sha256(path) != str(item["sha256"]):
'''
    # Patch only source closure, not the separate data validator.
    idx = text.index(old)
    text = text[:idx] + text[idx:].replace(old, new, 1)
    text = text.replace('"source_files_checked": checked,', '"source_files_checked": checked,\n        "archived_source_files_checked": archived_checked,')
    vpath.write_text(text)
    retired = root/'scripts/close_two_wave_v0707_governance.py'
    retired.write_text('''#!/usr/bin/env python3
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
''')
    (root/'.codex/cloud_verify.sh').write_text('''#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
VENV="$HOME/.cache/factorlab-two-wave-py311"
if [[ -x "$VENV/bin/python" ]]; then
  PYTHON="$VENV/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON="$(command -v python3.11)"
else
  PYTHON="$(command -v python)"
fi
"$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 required"'
"$PYTHON" scripts/repository_consistency.py --check
"$PYTHON" scripts/validate_theme_package.py
''')
    utility = root/'scripts/repository_consistency.py'
    spec = importlib.util.spec_from_file_location('repository_consistency', utility)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (root/'.github/workflows/ci.yml').write_text(module.CI_TEXT)
    for path in (root/'.github/workflows').glob('*'):
        if path.name != 'ci.yml' and path.is_file():
            path.unlink()
    test_src = root/'archive/maintenance_20260912/test_repository_consistency.py.template'
    target = root/'tests/unit/test_repository_consistency.py'
    shutil.copyfile(test_src, target)
    test_src.unlink()
    report = root/'docs/governance/REPOSITORY_MAINTENANCE_20260912.md'
    report.write_text(f'''# Repository reconciliation — 2026-09-12

This is maintenance, not a new scientific experiment. The scientific endpoint remains v0.7.8.

## Input and findings

Input commit: `{BASE}`; tree: `{TREE}`. The starting main was v0.7.6 (`ef29291535bc0fc239269ee9cb7c8e5a8512418c`).
v0.7.7/v0.7.8 adjudications existed on research branches but had not reached main.
README, INDEX, the human authority, AI entry and cloud-environment instructions had stale or contradictory current-state descriptions.
The initial scan found 4526 missing Markdown local-file targets in 49 imported documents; 524 Python files parsed without syntax errors.
Three large document pairs were byte-identical duplicates.

## Disposition

All {len(entries)} original files have a SHA256-preserved copy or remain byte-identical in place.
{redirects} imported document entries now explicitly redirect to archived originals; {removed} automatic strategy-skill files are removed from the discovery path.
{copies} unique archive copies preserve affected originals. Duplicate document payloads share an archive destination instead of being copied twice.
All market data, labels, scientific protocols, implementation modules, historical positive/negative results and original tests are unchanged.
The old v0.7.7 governance CLI is retired and cannot roll current authority back; pure historical helpers remain testable.
Frozen source verification follows explicit archive paths and still checks the original source digests; the immutable source manifest is not rewritten.

## Current organization

[Current entry](../../CONTINUE_HERE.md), [whitepaper](../research/TWO_WAVE_WHITEPAPER.md),
[authority](../../experiments/two_wave_m0_authority.json), [component inventory](repository_component_inventory.json),
[preservation map](repository_preservation_manifest_20260912.json), [archive policy](../../archive/README.md).
Archived relative links retain their original upstream context and are not claimed to be runnable package links.
All non-archived Markdown local-file links are checked, and all files receive an explicit component status.
Only the read-only bounded-theme-validation CI is allowed in the final working tree; no scientific one-shot remains active.

## Actual execution boundary

The session container could not resolve github.com for git clone. The authorized GitHub snapshot export supplied the exact input tree.
Local static checking is available; local Python is 3.13 and lacks pyarrow, so it is not the declared Python-3.11/full-data test environment.
Local maintenance tests and the standard-library validator are executed separately. Full package/data validation and the full regression suite use GitHub Actions Python 3.11.
The final execution receipt is written only after commands actually return success; this document is not itself a green-CI certificate.
Repository visibility was already public; this maintenance does not change visibility, copy private data into it, or claim a new privacy authorization.
''')
    communication = root/'docs/ops/cloud_local_communication.md'
    communication.write_text('''# 云端—本地沟通记录

## MAINT-20260912：仓库一致性整理

状态：本轮维护，不派发新的科学实验，不要求搬迁原始数据。
维护基线：ec0d49f1cec7d6c34d13af0fcfdb824687d57392。
本会话容器已取得固定仓库快照并执行静态检查及治理测试；Python 3.13 且缺少 pyarrow，不能冒充项目要求的 Python 3.11 全量环境。
正式 package/data 检查和全量 pytest 在 GitHub Actions Python 3.11 中运行；实际退出码与测试数量以验证回执和 CI 日志为准。
没有声称本地大模型已被自动派发或已反馈，也未要求重复搬运数据。

## 后续科学工作的外部证据边界

[当前接续入口](../../CONTINUE_HERE.md) 与 [v0.7.8 裁决](../../experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json) 是依据。
新时间样本 A 与新独立形态参考 B 必须同时满足准入并在评分前冻结协议。本轮不下载、不打分、不生成标签，也不把旧副本称作新证据。
若日后需要本地执行，应在此新增最小输入、代码版本、命令、实际退出码、结果位置及云端复核范围；目前没有待认领的本地计算任务。
''', encoding='utf-8')
    module.write(root)
    print(json.dumps(module.check(root), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
