import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('repository_consistency', ROOT/'scripts/repository_consistency.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_entire_checkout_is_consistent():
    result = MOD.check(ROOT)
    assert result['status'] == 'passed'
    assert result['preserved_original_files'] == 871
    assert result['active_workflow_count'] == 1
    assert result['current_broken_local_links'] == 0


def test_derived_documents_are_deterministic():
    assert MOD.render_documents(ROOT) == MOD.render_documents(ROOT)


def test_original_source_manifest_has_not_been_rewritten():
    baseline = MOD.load(ROOT, MOD.BASELINE)
    item = next(x for x in baseline['files'] if x['original_path'] == 'docs/governance/source_closure_manifest.json')
    assert item['disposition'] == 'retained_unchanged'
    assert MOD.digest(ROOT/item['preserved_path']) == item['sha256']


def test_original_science_and_data_are_preserved_in_place():
    for item in MOD.load(ROOT, MOD.BASELINE)['files']:
        name = item['original_path']
        protected = name.startswith(('src/', 'shared/', 'tests/', 'data/development/')) or (
            name.startswith('experiments/') and name != MOD.AUTHORITY)
        if protected:
            assert item['disposition'] == 'retained_unchanged', name
            assert MOD.digest(ROOT/name) == item['sha256'], name


@pytest.fixture
def authority_tree(tmp_path):
    for name in (MOD.AUTHORITY, MOD.A708, MOD.A707):
        p = tmp_path/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT/name).read_bytes())
    return tmp_path


@pytest.mark.parametrize('key', ['morphology_acceptance', 'trade_authority', 'production_authority'])
def test_unauthorized_promotion_fails(authority_tree, key):
    a = MOD.load(authority_tree, MOD.AUTHORITY)
    a[key] = True
    (authority_tree/MOD.AUTHORITY).write_text(json.dumps(a))
    with pytest.raises(ValueError, match='unauthorized promotion'):
        MOD.verify_authority(authority_tree)


def test_stale_next_step_fails(authority_tree):
    a = MOD.load(authority_tree, MOD.AUTHORITY)
    a['next_authorized_step'] = 'rerun in-sample direction'
    (authority_tree/MOD.AUTHORITY).write_text(json.dumps(a))
    with pytest.raises(ValueError, match='next action'):
        MOD.verify_authority(authority_tree)


def test_current_representation_cannot_revert_to_exact_tuple(authority_tree):
    a = MOD.load(authority_tree, MOD.AUTHORITY)
    a['component_authority']['parent_identity']['version'] = 'v0.5.2'
    (authority_tree/MOD.AUTHORITY).write_text(json.dumps(a))
    with pytest.raises(ValueError, match='representation'):
        MOD.verify_authority(authority_tree)


def test_false_external_evidence_admission_fails(authority_tree):
    a = MOD.load(authority_tree, MOD.AUTHORITY)
    a['external_validation_availability']['v0708']['direction_scoring_opened'] = True
    (authority_tree/MOD.AUTHORITY).write_text(json.dumps(a))
    with pytest.raises(ValueError, match='blocked-state'):
        MOD.verify_authority(authority_tree)


def test_archive_tampering_is_not_an_exemption(tmp_path):
    source = tmp_path/'archive/original.txt'
    source.parent.mkdir(parents=True)
    source.write_text('original')
    baseline = {'files': [{'original_path': 'old.txt', 'preserved_path': 'archive/original.txt',
                          'sha256': MOD.digest(source), 'disposition': 'archived_with_redirect'}]}
    p = tmp_path/MOD.BASELINE
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(baseline))
    MOD.validate_preservation(tmp_path)
    source.write_text('tampered')
    with pytest.raises(ValueError, match='lost'):
        MOD.validate_preservation(tmp_path)


@pytest.mark.parametrize('path', ['../outside', '/tmp/outside', 'archive/../../outside', ''])
def test_archive_path_escape_is_rejected(tmp_path, path):
    with pytest.raises(ValueError, match='unsafe'):
        MOD.safe_path(tmp_path, path)


def test_broken_live_links_fail_but_archives_keep_historical_context(tmp_path):
    (tmp_path/'current.md').write_text('[missing](missing.md)')
    (tmp_path/'archive').mkdir()
    (tmp_path/'archive/history.md').write_text('[old](old-unshipped.md)')
    n, errors = MOD.check_links(tmp_path)
    assert n == 1 and errors == ['current.md: missing.md']


def test_unknown_component_cannot_silently_enter_inventory():
    with pytest.raises(ValueError, match='unclassified'):
        MOD.classify('unreviewed.bin', ROOT, {})


def test_retired_governance_cli_cannot_roll_back_authority():
    before = MOD.digest(ROOT/MOD.AUTHORITY)
    result = subprocess.run([sys.executable, str(ROOT/'scripts/close_two_wave_v0707_governance.py')],
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert 'RETIRED' in result.stderr
    assert before == MOD.digest(ROOT/MOD.AUTHORITY)


def test_historical_snapshot_helper_does_not_mutate_current_input():
    spec = importlib.util.spec_from_file_location('historical_governance', ROOT/'scripts/close_two_wave_v0707_governance.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    a = MOD.load(ROOT, MOD.AUTHORITY)
    before = deepcopy(a)
    result = json.loads(old.RESULT_PATH.read_text())
    snapshot = old.updated_authority(a, result)
    assert a == before
    assert snapshot['schema'] == 'two_wave_m0_authority@1.32'
    assert a['schema'] == 'two_wave_m0_authority@1.33'
