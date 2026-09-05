#!/usr/bin/env python3
"""Create-only, allowlisted archival of one successful private research run.

No market downloads, rerun, parameter selection, model change, or broad git add.
The workflow downloads the named immutable artifact; this verifies its contents.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

CODE_COMMIT = 'ba871b71edc3994c9e611f2451d414bb4f33cfcb'
RUN_ID = 33961057778
ARTIFACT_ID = 9968031399
ARTIFACT_SHA256 = '1f6e6259f3e526b0049a051e9319b6f7554176f195acffa492fb968735c5bb75'
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'cloud_results/two_wave_same_scale_delivery'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, required=True)
    args = p.parse_args()
    source = args.source_root.resolve()
    if DEST.exists():
        raise SystemExit('Refusing to overwrite an existing delivery')
    tests = ET.parse(source/'structure_tests.xml').getroot()
    suites = [tests] if tests.tag == 'testsuite' else tests.findall('testsuite')
    totals = {k: sum(int(s.get(k, '0')) for s in suites) for k in ('tests','errors','failures','skipped')}
    assert totals == {'tests':304,'errors':0,'failures':0,'skipped':0}, totals
    validation = json.loads((source/'structure_validation.json').read_text())
    assert validation['source_files_checked'] == 473 and validation['immutable_tool_count'] == 15
    assert validation['data_product_count'] == 14 and not validation['fresh_oos']
    assert not validation['production_authority']
    results = [('two_wave_structure_v04','v04'),('two_wave_direction_v041','v041')]
    checked = 0
    plans = []
    summaries = {}
    for name, target in results:
        folder = source/'cloud_results'/name
        manifest = json.loads((folder/'run_manifest.json').read_text())
        assert manifest['actual_git_commit'] == CODE_COMMIT
        for filename, sha in manifest['source_sha256'].items():
            assert digest(ROOT/filename) == sha, filename
        for filename, sha in json.loads((folder/'output_sha256.json').read_text()).items():
            q = (folder/filename).resolve()
            assert q.is_relative_to(folder.resolve()) and not q.is_symlink()
            assert digest(q) == sha, filename
            checked += 1
        summary = json.loads((folder/'summary.json').read_text())
        assert summary['status'] == 'morphology_replication_not_yet_accepted'
        assert not summary['pnl_computed'] and not summary['trade_authority']
        summaries[target] = summary
        for q in folder.rglob('*'):
            if not q.is_file():
                continue
            relative = q.relative_to(folder)
            if (relative.parts[0] in ('5m_offset_0','gallery') or q.name == 'summary.json'
                or str(relative) in ('run_manifest.json','legacy_case_reaudit.json','output_sha256.json')):
                destrel = Path(target)/relative
                if str(relative) == 'output_sha256.json':
                    destrel = Path(target)/'full_run_output_sha256.json'
                plans.append((q, destrel))
    assert summaries['v04']['prefix_checks_passed'] == 96
    assert summaries['v041']['independent_D1_prefix_checks_passed'] == 24
    assert checked == 588
    for name in ('structure_tests.xml','structure_validation.json','structure_environment.txt'):
        plans.append((source/name, Path(name)))
    assert sum(q.stat().st_size for q, _ in plans) < 45_000_000
    copied = {}
    for q, rel in plans:
        assert not q.is_symlink() and not rel.is_absolute() and '..' not in rel.parts
        dest = DEST/rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(q, dest)
        copied[str(rel)] = {'sha256': digest(dest), 'source_path': str(q.relative_to(source)), 'bytes': dest.stat().st_size}
    # Plain Markdown indices work inside GitHub; HTML indices work after download.
    for name in ('v04','v041'):
        folder = DEST/name/'gallery'
        index = json.loads((folder/'index.json').read_text())
        lines = ['# 图形审计索引', '', '开发期图形，不是独立人类真值，也不是交易信号。空白区域不自动代表震荡。',
                 '', '| 案例 | 价格与形态 | ER16/W128诊断 |', '|---|---|---|']
        for item in index:
            case = item['case']
            lines.append(f'| {case} | [价格图]({case}.png) | [ER图]({case}_ER.png) |')
        (folder/'README.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    (DEST/'README.md').write_text('''# 同尺度两浪研究：持久化审查包

代码提交：`ba871b71edc3994c9e611f2451d414bb4f33cfcb`。正式运行：`33961057778`。

本目录保存全部主5分钟候选、互斥分段、全长含未决分区、确认事件带，全部41个D0/C2G审计案例、98个D1已发布案例，以及六视图所有组的摘要。其他视图的完整逐条账本保留在源运行工件，并可由已提交代码重放。

- [D0/C2G图集：保留旧案例及失败模式](v04/gallery/README.md)
- [D1全部98个发布段：按时间排序、不挑成功样本](v041/gallery/README.md)
- [D0/C2G六视图摘要](v04/summary.json)
- [D1六视图摘要、偏移稳健性及微扰](v041/summary.json)
- [主视图D1分段](v041/5m_offset_0/D1/segments.json)
- [主视图D1全长分区，包含未覆盖与未决](v041/5m_offset_0/D1/partition.json)
- [归档清单与运行来源](delivery_manifest.json)

`full_run_output_sha256.json`是完整源工件的校验清单，不表示本目录含有其他视图的全部逐条文件。`delivery_manifest.json`逐项列明真正复制的内容及其源路径和哈希。

304项测试及120次独立截断重放通过，不代表形态验收通过。主视图仅覆盖4521/70114根（6.448%）；D1为32上涨、31下跌、1震荡、34不确定。其他5m偏移与主视图的结构区间交并比仅约12%—20%。保留`morphology_replication_not_yet_accepted`，没有收益计算、第三浪或交易权限。

形态区间为事后描述，确认条带不是实时交易状态。必须尊重原始`available_at`及`effective_information_time`，不能回填或前向延长为当时已知信号。
''', encoding='utf-8')
    save(DEST/'delivery_manifest.json', {
        'source_run_id':RUN_ID,'source_code_commit':CODE_COMMIT,'source_artifact_id':ARTIFACT_ID,
        'source_artifact_zip_sha256':ARTIFACT_SHA256,
        'zip_sha256_verified_in_analysis_container':True,
        'collector_verification':'all source outputs checked against source per-file hashes; current code hashes checked',
        'source_outputs_hash_checked':checked,'tests':totals,'independent_prefix_checks':120,
        'copied_file_count':len(copied),'copied_bytes':sum(x['bytes'] for x in copied.values()),
        'copied_files':copied,'generated_indices':['README.md','v04/gallery/README.md','v041/gallery/README.md'],
        'morphology_accepted':False,'trading_authority':False,'archive_does_not_rerun_or_change_model':True})
    print(json.dumps({'destination':str(DEST.relative_to(ROOT)), 'files':len(copied), 'hash_checks':checked, 'tests':totals}))


if __name__ == '__main__':
    main()
