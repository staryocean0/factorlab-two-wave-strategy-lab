#!/usr/bin/env python3
"""Render/check the current control plane without running scientific experiments.

Python standard library only. --write refreshes derived documentation/inventory;
it never updates research authority, source, labels, data, or experiment results.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = 'experiments/two_wave_m0_authority.json'
BASELINE = 'docs/governance/repository_preservation_manifest_20260912.json'
INVENTORY = 'docs/governance/repository_component_inventory.json'
A708 = 'experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json'
A707 = 'experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json'
EXPECTED = 'v0708_external_validation_evidence_gap_no_candidate_opened'
IGNORE = {'.git', '__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache'}
CI_TEXT = '''name: bounded-theme-validation
on:
  push:
  pull_request:
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: python -m pip install -e .
      - name: Current authority, documentation, archives, links and inventory
        run: python scripts/repository_consistency.py --check
      - name: Frozen source closure, data and tool boundary
        run: python scripts/validate_theme_package.py
      - name: Full regression suite
        run: python -m pytest -q
      - name: Tests must not mutate tracked evidence
        run: git diff --exit-code
'''


def load(root: Path, relative: str):
    return json.loads((root / relative).read_text(encoding='utf-8'))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not relative:
        raise ValueError(f'unsafe repository path: {relative}')
    result = root / p
    if result.is_symlink() or not result.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'path leaves repository: {relative}')
    return result


def files(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob('*')
                  if p.is_file() and not any(x in IGNORE or x.endswith('.egg-info')
                                            for x in p.relative_to(root).parts))


def link(page: str, target: str, title: str | None = None) -> str:
    rel = os.path.relpath(target, Path(page).parent).replace(os.sep, '/')
    return f'[{title or target}]({rel})'


def verify_authority(root: Path) -> dict:
    a, e, d = load(root, AUTHORITY), load(root, A708), load(root, A707)
    if a.get('global_status') != e['primary_category'] or e['primary_category'] != EXPECTED:
        raise ValueError('machine authority / v0.7.8 adjudication disagree')
    if a.get('current_scientific_revision') != 'v0.7.8':
        raise ValueError('current scientific revision drifted')
    if a.get('next_authorized_step') != e['next_authorized_step']:
        raise ValueError('next action differs from the authoritative availability adjudication')
    for key in ('morphology_acceptance', 'trade_authority', 'production_authority'):
        if a.get(key) is not False or e.get(key) is not False or d['authority'].get(key) is not False:
            raise ValueError(f'unauthorized promotion: {key}')
    if a['component_authority']['parent_direction'].get('winner') is not None:
        raise ValueError('direction winner must remain null')
    p = a['component_authority']['parent_identity']
    if p.get('active_semantic_parent_authority') is not None or p.get('version') != 'v0.7.4':
        raise ValueError('current representation / semantic-parent authority drift')
    if a['current_independent_reference_calibrated_qualification_authority'] is not None:
        raise ValueError('qualification has not obtained independent reference authority')
    if not a.get('no_current_direction_challenger_authorized'):
        raise ValueError('in-sample direction line was reopened')
    if a['external_validation_availability']['v0708']['adjudication'] != A708:
        raise ValueError('v0.7.8 source pointer drift')
    for key in ('candidate_identity_frozen', 'external_validation_protocol_opened',
                'direction_scoring_opened', 'threshold_change_opened', 'result_opened',
                'temporal_trigger_A_satisfied', 'independent_reference_trigger_B_satisfied'):
        if a['external_validation_availability']['v0708'].get(key) is not e[key] or e[key] is not False:
            raise ValueError(f'v0.7.8 blocked-state drift: {key}')
    v = a['component_authority']['parent_direction']['v0707']
    for key, expected in [('qualified_publication_count', d['stage_a']['v0618_qualified_publication_count']),
                          ('v0625_rescue_count', d['stage_a']['v0625_rescue_count']),
                          ('D1_case_exact_count', d['stage_b']['D1_case_exact_count']),
                          ('v0625_case_exact_count', d['stage_b']['v0625_case_exact_count'])]:
        if v[key] != expected:
            raise ValueError(f'v0.7.7 authority / formal result disagreement: {key}')
    for key in ('v0647_external_validation_weakness_binding', 'v0648_external_validation_weakness_binding'):
        if a['f3_lifecycle_direction_transplant']['v0707'].get(key) is not True:
            raise ValueError(f'external negative evidence lost: {key}')
    retention = a['counteroffensive_component_retention']
    if 'awaiting' in retention['tuple_birth_causal_adjacency_rule'] or 'next' in retention['direction_D1_v0625']:
        raise ValueError('completed transplantation still described as pending')
    return a


def current_block(root: Path, page: str) -> str:
    a, e, d = load(root, AUTHORITY), load(root, A708), load(root, A707)
    x, y = d['stage_a'], d['stage_b']
    return f'''当前科学版本：**{a['current_scientific_revision']}**；状态：`{a['global_status']}`。

唯一机器权威：{link(page, AUTHORITY)}。v0.7.8 证据来源：{link(page, A708)}。
维护整理不是新的科学实验，不把版本号推进到 v0.7.9。

| 项目 | 当前真实状态 |
| --- | --- |
| 父结构研究表示 | F3 persistence-dominant quintet → v0.7.4 prefix-causal lifecycle；仅 Development 支持 |
| raw projection / publication | v0.7.5 已移植历史 v0.6.4/v0.6.5 原则；{x['publication_count']} 个发布对象 |
| qualification | v0.7.6 已移植 v0.6.18；{x['v0618_qualified_publication_count']} 个合格发布对象；语义支持 {y['v0618_qualified_semantic_support_cases']}/11 |
| direction | v0.7.7 已完成；v0.6.25 保留为非胜者贡献，D1 仅为历史基线 |
| direction 对照结果 | {x['v0625_rescue_count']} 个发布级不确定状态得到分类；Development 锚定子集 D1 与 v0.6.25 均为 {y['D1_case_exact_count']}/9 exact，未证明语义提升 |
| 当前权限 | semantic-parent authority=null；direction winner=null；morphology/trade/production=false |
| 下一科学步骤 | 同时具备新时间样本 A 和新独立形态标签 B，先预注册再评分；当前 A=false、B=false |

v0.6.47 的时间复制弱点与 v0.6.48 的独立参考校准弱点继续有效。
11 个锚定案例及 115 个合格发布对象属于 Development，不是新的样本外证据。
'''


def render_documents(root: Path) -> dict[str, str]:
    a = load(root, AUTHORITY)
    preservation = load(root, BASELINE)
    archived = {x['original_path']: x['preserved_path'] for x in preservation['files']
                if x['disposition'] != 'retained_unchanged'}
    docs: dict[str, str] = {}
    def put(page, title, body, state=False):
        docs[page] = (f'# {title}\n\n<!-- Generated by scripts/repository_consistency.py; do not hand-edit. -->\n\n'
                      + (current_block(root, page) + '\n' if state else '') + body.strip() + '\n')
    p = 'README.md'
    put(p, '中证1000 Two-Wave 父结构识别研究', f'''
研究目标是识别同尺度的两个完整波形，并描述父结构为 Range / UpTrend / DownTrend / Uncertain。
本仓库不具有交易或生产权限。

从 {link(p, 'CONTINUE_HERE.md', '接续入口')} 开始；
{link(p, 'docs/INDEX.md', '文档索引')}、{link(p, 'docs/research/TWO_WAVE_WHITEPAPER.md', '当前白皮书')}、
{link(p, 'docs/governance/REPOSITORY_MAINTENANCE_20260912.md', '整理与验证记录')} 分别负责导航、方法与维护溯源。

本仓库保留冻结的研究代码和全部实验正负结果。目录中存在旧版本，不等于该版本仍是现行方案。
{link(p, INVENTORY, '全文件组件登记')} 为每个文件标记 current、frozen、historical 或 archived 身份。

Python 包版本仍为 0.1.0；这是包装版本，不是科学协议版本。正式测试环境为 Python 3.11。

```bash
python -m pip install -e .
python scripts/repository_consistency.py --check
python scripts/validate_theme_package.py
python -m pytest -q
```

自动 CI 仅做一致性、数据/源码完整性和回归测试；不重跑形态评分、不拉取外部行情、不修改权威文件。
''', True)
    p = 'CONTINUE_HERE.md'
    put(p, '从这里接续', f'''
先读 {link(p, 'AGENTS.md')}、{link(p, 'docs/research/TWO_WAVE_WHITEPAPER.md')}，再按 {link(p, 'docs/INDEX.md')} 定位代码和证据。

v0.7.7 与 v0.7.8 均已产生裁决；不要重开 salvage staircase、在样本内调整 direction，或把待取外部证据伪装成已完成验证。
维护期间可以修复入口、校验器和测试；不能修改科学阈值、标注、原始行情或历史结果。

下一科学动作（逐字来自机器裁决）：

> {a['next_authorized_step']}

本轮整理基于 `ec0d49f1cec7d6c34d13af0fcfdb824687d57392`；历史 main 当时停在 v0.7.6。
GitHub 的实际分支指针与检查结果是合并是否完成的依据，本文件不会自称某次尚未执行的合并成功。
''', True)
    p = 'ai-readme.md'
    put(p, 'Two-Wave AI 入口', f'''
本仓库是 `staryocean0/factorlab-two-wave-strategy-lab`，不是 REAKA 多因子选股项目。
先读 {link(p, 'CONTINUE_HERE.md')} 和 {link(p, 'AGENTS.md')}。
原 FactorLab 混合项目 AI 索引已退役，原文仅保存在 {link(p, archived[p], '导入快照')}。
''')
    p = 'docs/research/TWO_WAVE_M0_AUTHORITY.md'
    put(p, 'Two-Wave M0 当前人类权威说明', f'''
本页由机器权威和正式裁决派生，不另设一套可漂移的状态。
完整研究方法见 {link(p, 'docs/research/TWO_WAVE_WHITEPAPER.md')}。
旧的逐版本追加说明在 {link(p, archived[p], '历史权威快照')}，其中“下一步”只属于当时的阶段。

历史完整识别器 v0.4.3 仅是比较基线；没有被偷偷升级为独立形态验收通过。
exact-consecutive five-ridge tuple 不再具有当前 semantic-parent authority。
''', True)
    p = 'docs/research/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md'
    put(p, '方向贡献台账：当前裁决与历史索引', f'''
v0.6.25 可以在新的生命周期对象上运行，也有发布级分类增量；但不能将该增量冒充人工语义正确率改善。
其合法结论是“保留 Development 贡献，不设方向胜者”。

{link(p, A707, 'v0.7.7 正式裁决')}；{link(p, A708, 'v0.7.8 外部证据缺口裁决')}。
全部旧信息族、失败归因与数值保存在 {link(p, archived[p], '冻结的历史贡献台账')} 及各自实验目录。
关闭的信息族不因整理、改名或增加文件而重新开放。
''', True)
    p = 'docs/research/TWO_WAVE_WHITEPAPER.md'
    stages = [('extremum_ridge_v052.py', 'TCSS extrema / ridge 支撑基础设施，保留但不等于语义父对象'),
              ('ridge_semantic_objectization_v0701.py', 'F3 非连续五脊线对象定义；不能任意放宽相邻约束'),
              ('f3_prefix_causal_lifecycle_v0704.py', 'observed / dormant / reobserved / certified 追加式生命周期'),
              ('f3_provisional_lifecycle_publication_v0705.py', '顺序 raw projection 与 first-valid immutable publication'),
              ('f3_lifecycle_qualification_transplant_v0706.py', '出版时前缀上的 v0.5.4 / v0.6.18 qualification'),
              ('lifecycle_qualified_direction_v0707.py', 'D1 基线及固定 v0.6.25 rescue 的移植比较')]
    rows = '\n'.join('| ' + link(p, 'src/factor_lab/visual_structure/two_wave/' + name, name) + ' | ' + text + ' |' for name, text in stages)
    put(p, 'Two-Wave 当前研究白皮书', f'''
## 1. 定义、假说与权限必须分开

两个完整波形至少要表达 L0→H1→L1→H2→L2 或其高点起算对称形式，不能把两条单向价格腿称为两浪。
识别父结构的几何方向不等于预测收益，也不证明第三浪、趋势延续或均值回归具有交易价值。
原始用户目标及退出规则完整保存在 {link(p, archived['docs/user/two_wave_strategy_handoff_prompt.md'], '原始需求原文')}；本轮没有改写这些规则。

## 2. 第一断点和重建边界

v0.7.0 的共同尺度 ridge 支持为 10/11，而 exact consecutive five-ridge tuple 为 3/11；
L1→L2 损失七例，L2→L3 不再损失。应保留 ridge 基础设施，修复对象化，而不是把所有下游成果判错。
F3 在同一尺度选择交替的五个 ridge；被跨过的 ridge 的因果存活尺度必须严格低于两侧所选 ridge 的较小存活尺度。
这不是用人工案例拟合 bar-distance 容差，也不是所有五点子序列都可晋升为父结构。

F3 静态支持 8/11。v0.7.2/v0.7.3 的永久因果证书只支持 7/11：缺失的显式 death 证据不能从未来借用。
v0.7.4 因此区分“当时已观察到”与“永久证据已齐备”，通过追加生命周期保留 8/11 的当时 live 支持。
Dormant 历史对象不算当前语义支持；认证事件也不能反写 first observation。

## 3. 当前实现链及相应语义

| 实现文件 | 职责 / 边界 |
| --- | --- |
{rows}

raw publication 保留 first-valid 身份；未来可用的更好投影只作为新证据，不改写已发布身份。
qualification 和 direction 均只读 publication confirmation 时刻及以前的 bar 前缀。
v0.6.18 仅把 inefficient_leg 与 jump_dominated_leg 从硬否决移至诊断，其余门槛不变。
v0.6.25 仅救援 D1-Uncertain，并保留原 unanimous erosion-consensus 与 0.10 margin；不得覆盖 D1 已明确分类。

## 4. 成果能够说明什么

v0.7.5 发布 1543 个生命周期对象，其中 1478 个得到永久认证、65 个在截止时仍未解决；raw 语义支持 9/11。
v0.7.6 的原实现与第一次重试无效，唯一正式重试 run 为 34687608997；修复后 115 个发布对象通过 v0.6.18，语义支持仍为 9/11。
v0.7.7 在 115 个合格对象上救援 19 个发布级不确定状态，但九个有语义支持的案例中 D1/v0.6.25 都是 7/9 exact、2/9 uncertain。
这证明了移植的可运行性及部分 Development 支持，**没有证明样本外形态准确性，更没有证明 alpha**。

这些数字有不同分母：案例、发布对象、严格跨 offset 配对不可混用。11 例 salvage 支持不能推出全体场景的 precision/recall。
未认证对象不能改称已认证；开发集中的较高覆盖也不能替代独立标签验证。

## 5. 必须保留的反证与下一步

v0.6.47 的时间复制中 D1 exact 为 242/253，v0.6.25 为 238/253。
v0.6.48 仅 16/120 个候选被独立参考确认，D1/v0.6.25 在这些对象上的 exact 均为 5/16。
两组弱点不会被这次重建或维护覆盖掉；v0.7.8 没有找到同时满足 A/B 的可准入新证据。
新时间数据与新独立形态标签必须有冻结 provenance、案例全集、预注册方案与评分时点，不能按结果反向挑选。

## 6. 数据、测试与可复现性

工作树内的行情只有 data/manifest.json 定义的 14 个 2015—2020 Development 产品，共 749337 行。
v0.6.47 曾按冻结协议消费外部 2024/2025/2026 时间复制材料；“未存入本仓”不代表“研究者未看过”。
默认禁止自行重采样，历史 validation_resample_v0647 是有开发集及 native 对照的专门验证例外，不是任意采样许可。
正式环境 Python 3.11；本仓没有在线执行、期权选择或账户下单入口授权。

一般维护检查：一致性校验器 → 冻结数据/源码校验器 → 全量 pytest。
正式研究脚本只用于已冻结协议的历史复现，不能因为还在 scripts/ 就默认再次获得评分权限。
所有历史白皮书与工作流另列为 upstream reference，不是本白皮书的同级 current authority。

完整证据入口：{link(p, 'docs/INDEX.md')}；全文件身份：{link(p, INVENTORY)}；保留原件：{link(p, BASELINE)}。
''', True)
    p = 'docs/INDEX.md'
    protocols = [x for x in files(root) if x.startswith('docs/research/') and x.endswith('_PROTOCOL.md')]
    evidence = [x for x in files(root) if x.startswith('experiments/') and Path(x).name in {'ADJUDICATION.json', 'RESULT_CARD.md'}]
    put(p, '当前文档与历史证据索引', f'''
## 当前入口

- {link(p, 'CONTINUE_HERE.md', '接续入口')} / {link(p, AUTHORITY, '机器权威')} / {link(p, 'docs/research/TWO_WAVE_M0_AUTHORITY.md', '人类权威')}
- {link(p, 'docs/research/TWO_WAVE_WHITEPAPER.md', '当前白皮书')} / {link(p, 'docs/research/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md', '方向贡献台账')}
- {link(p, 'docs/governance/data_usage_declaration.json', '当前数据边界')} / {link(p, 'docs/governance/package_scope.json', '当前仓库范围')}
- {link(p, INVENTORY, '全文件组件身份')} / {link(p, 'docs/governance/REPOSITORY_MAINTENANCE_20260912.md', '维护审计')} / {link(p, 'archive/README.md', '归档说明')}

## 冻结基础设施合同：兼容性，不授予科学晋升

''' + '\n'.join('- ' + link(p, x) for x in [
'docs/ops/timing_infrastructure_four_layer_inventory@1.0.json',
'docs/ops/timing_layer1_datahub_clock_split@1.0.json',
'docs/ops/timing_layer2_measurement_plane@2.3.json',
'docs/ops/timing_layer3_strategy_architecture@2.2.json',
'docs/ops/timing_strategy_identity_registry@2.2.json',
'docs/ops/timing_four_layer_port_contracts@1.1.json']) + '\n\n## 已冻结科学协议（历史，不是待办队列）\n\n'
+ '\n'.join('- '+link(p,x,Path(x).name) for x in protocols)
+ '\n\n## 结果卡与裁决（包括失败、无效及 blocked）\n\n'
+ '\n'.join('- '+link(p,x,x.removeprefix('experiments/')) for x in evidence), True)
    p = 'docs/user/cloud_execution_prompt.md'
    put(p, '云端接续工作流', f'''
先读 {link(p,'CONTINUE_HERE.md')} 和 {link(p,'AGENTS.md')}，按当前权威工作，不回到最初识别器搭建阶段。
直接运行可用的静态检查；正式依赖/数据无法在当前会话满足时记录原因，再选择适用的执行环境。
默认任务是维护与证据准入核对，不是新 direction 实验。CI 成功不等于形态验收。
原始 prompt 仅作 {link(p,archived[p],'历史记录')}。
''')
    p = 'docs/user/two_wave_strategy_handoff_prompt.md'
    put(p, '用户原始目标与当前阶段', f'''
用户原始需求逐字保存在 {link(p,archived[p],'原始需求快照')}，包括完整周期定义、因果性、第三浪研究顺序及反向结构突破退出规则。
本次整理没有撤销这些需求，只防止原始“先做第一版”的叙述盖过当前研究状态。
当前接续入口为 {link(p,'CONTINUE_HERE.md')}；不得把原始远期交易设想视为当前交易许可。
''')
    p = 'data/README.md'
    put(p, '冻结 Development 行情与已消费的外部证据', f'''
本目录只有 DataHub 冻结的 14 个中证1000产品、749337行，范围 2015-01-05 至 2020-12-31。
{link(p,'data/manifest.json','数据清单')} 和 {link(p,'docs/governance/data_usage_declaration.json','当前使用边界')} 定义实际范围和权限。
timestamp 是带时区 UTC bar-end，bar_end_shanghai 是同一时刻的上海时间；原始 source serialized 字符串另存审计。
不填补 volume、不生成行情、不把指数信号当作可成交价格；默认不另造 wall-clock bar。

2021 年以后行情没有存入本工作树。但 v0.6.47 已在外部读取 2024/2025/2026 时间复制材料，截止 2026-08-21；
这些已消费数据不能因为换仓或未存入本仓就改称 fresh OOS。冻结 validation_resample_v0647 只是专门验证例外。
本轮维护不下载新行情。{link(p,'CONTINUE_HERE.md','当前接续条件')} 仍要求新时间证据与独立形态标签同时准入。
''')
    p = 'scripts/README.md'
    put(p, '执行入口及退役边界', f'''
当前日常验证入口是 repository_consistency.py 与 validate_theme_package.py；前者不运行形态计算，后者检查冻结文件、14个行情产品与工具边界。
repository_consistency.py --write 仅刷新派生文档和组件清单，不写机器科学权威。
close_two_wave_v0707_governance.py 的写入 CLI 已退役；其纯历史辅助函数保留以兼容原回归测试。

其余版本化 research/evaluate/build 脚本按 {link(p,INVENTORY,'全文件清单')} 保留历史复现身份，不默认授权再次评分。
每次复现必须先找到 {link(p,'docs/INDEX.md','冻结协议与对应裁决')}；不得以维护为理由重跑已消耗的外部样本并冒称新证据。
本仓没有获准的交易或账户执行入口；基础设施 workflow 构造器不是科学晋升指令。
''')
    p = 'tests/README.md'
    put(p, '测试与证据的对应关系', f'''
正式环境 Python 3.11；完整入口为 python -m pytest -q。原有测试全部保留，不为维护修改科学断言。
新增 test_repository_consistency.py 检查当前权威/文档一致、原件保留、文件分类、链接与退役入口，并包含伪造准入、越权晋升、档案篡改的失败用例。

测试通过只证明被覆盖的实现与治理约束，不等于所有科学假说正确或 morphology_acceptance=true。
脚本、文档与测试身份见 {link(p,INVENTORY,'组件清单')}；方法及当前证据边界见 {link(p,'docs/research/TWO_WAVE_WHITEPAPER.md','白皮书')}。
''')
    p = 'experiments/README.md'
    put(p, '实验存档与当前状态', f'''
唯一可变 current authority 是 {link(p,AUTHORITY)}，其余实验文件按冻结阶段保留。
v0.7.8 是可用性审计而不是新科学评分；result_opened=false 不意味着没有行政裁决文件。
{link(p,'docs/INDEX.md','协议、结果卡与裁决索引')} 列出全部历史证据。
SCORING_BLOCKED、PRELABEL 等文件记录生成时的检查点，不推翻之后正式的 FINAL_REFERENCE_FREEZE / ADJUDICATION。
v0.7.6 的原始无效实现和失败重试保留溯源；只有其 ADJUDICATION 指定的正式重试可以解释为有效结果。
''')
    p = 'experiments/two_wave_independent_reference_label_v0648/README.md'
    put(p, 'v0.6.48 已完成；早期 blocked 文件仅为历史检查点', f'''
当前该阶段裁决见 {link(p,'experiments/two_wave_independent_reference_label_v0648/ADJUDICATION.json')}。
本目录 SCORING_BLOCKED.json 是标注前的冻结检查点，不是当前待办。不得重写或删除该原始证据。
独立参考校准未全门通过的结论继续约束后续研究；它不等于“仍在等待第一轮标注”。
''')
    p = 'docs/ops/README.md'
    put(p, '基础设施合同与上游白皮书导航', f'''
本目录 JSON 为冻结的 FactorLab 基础设施兼容合同。Markdown 旧白皮书通过显式入口连接其原件，仅作为上游参考。
Two-Wave 科学现状只读 {link(p,'docs/research/TWO_WAVE_WHITEPAPER.md','当前白皮书')} 和 {link(p,AUTHORITY,'机器权威')}。
执行范围、15 工具冻结前缀、未安装第 16 候选工具等边界仍保留。
''')
    for p in ('docs/user/README.md', 'docs/00-index.md'):
        put(p, 'Two-Wave 导航入口', f'本仓有效导航为 {link(p,"docs/INDEX.md")}。旧 FactorLab 全项目索引已经归档，不再作为执行入口。')
    p = 'archive/README.md'
    put(p, '历史归档：不具有当前执行权', f'''
upstream_seed/ 保留初始导入的跨项目文档与退役自动发现技能；control_plane_20260912/ 保留整理前的所有被维护文件原件。
相同内容只保留一份；{link(p,BASELINE,'保留清单')} 记录每个旧地址、原始 SHA256 与现存原件地址。
冻结源清单不改写：校验器根据显式重定位表到原件检查原 SHA256，不把归档当作豁免校验。

归档 Markdown 的相对链接按原始上游仓库语境解释，其中可能指向本 bounded package 从未导入的页面。
这些链接不计作当前可运行入口；当前文档链接必须全部可解析。旧“current/next/blocked”只表示历史时点。
历史协议、实验原始文件与被代码引用的组件通常就地保留，并在全文件清单中标为 historical 或 frozen。
''')
    p = '.codex/CLOUD_ENVIRONMENT.md'
    put(p, 'Two-Wave 环境与验证', f'''
当前入口：{link(p,'CONTINUE_HERE.md')}，不固定旧 codex 分支或 CL-003 待办。
正式 Python 版本为 3.11，与 pyproject.toml 和 CI 一致。
已有环境可使用 cloud_setup.sh / cloud_maintenance.sh 安装依赖；cloud_verify.sh 验证当前一致性与全部冻结数据。
这些脚本只准备/验证环境，不开启外部数据评分、账户回测或自动交易。
自动发现的 strategy-slice-rebuild 技能已归档，本仓不把完整策略推广工作流作为当前 M0 任务。
''')
    p = 'AGENTS.md'
    old_agents = (root / archived[p]).read_text(encoding='utf-8')
    cloud_section = old_agents[old_agents.index('## 云端—本地交接协议'):]
    put(p, 'Two-Wave 当前协作合同', f'''
## 读取顺序与唯一权威

1. {link(p,'CONTINUE_HERE.md')} 和 {link(p,AUTHORITY)}。
2. {link(p,'docs/research/TWO_WAVE_WHITEPAPER.md')}、{link(p,'docs/INDEX.md')}。
3. {link(p,'docs/governance/data_usage_declaration.json')}、{link(p,'docs/governance/layer3_tool16_candidate_slot.json')}。
4. 按任务读取冻结协议、原始用户需求快照及对应代码/测试。

先读 current，再读历史。旧协议的局部前置状态不能覆盖较晚正式裁决；归档与上游文档不发出当前执行指令。
维护不等于新科学实验。不得修改 source/label/data/result 或调整阈值来使校验通过。

## 数据和权限

工作树内行情为 14 个 2015—2020 Development 产品。外部 2024/2025/2026 样本曾被 v0.6.47 读取，不能再称未消费样本。
默认不下载后续数据、不自行造 bar；仅专门冻结的 validation_resample_v0647 具有历史验证用途。
任何新外部验证先满足 v0.7.8 A/B 证据准入并预注册，再评分；跨仓复制不等于独立样本。

tool_registry_v1_5 的十五工具前缀、Layer 3 architecture@2.2、identity registry@2.2 均保持冻结。
第十六工具只是候选槽，未安装；morphology、trade、production 权限仍为 false，direction winner 为 null。
不运行第三浪/PnL/期权选择/账户执行，不改 Layer 4 或本地 current 指针。

## 代码、文档、测试一起维护

复用 src/ 内的冻结组件与 tests/ 回归测试，不因版本旧就删掉依赖。
仅维护 scripts/repository_consistency.py 管理的派生页面；修改机器权威必须有新的正式裁决。
更新派生页面和清单：`python scripts/repository_consistency.py --write`。
验收：`python scripts/repository_consistency.py --check`、`python scripts/validate_theme_package.py`、`python -m pytest -q`。
CI 仅验证，不评分、不写权威；一次性工作流完成后必须从 .github/workflows 移除。

{cloud_section}
''', True)
    for row in preservation['files']:
        p = row['original_path']
        if row['disposition'] == 'archived_with_redirect' and p not in docs:
            put(p, f'已归档参考：{Path(p).name}',
                f'本页不再是当前执行或权威入口。原件：{link(p,row["preserved_path"],"冻结原文")}。\n\n'
                f'Two-Wave 当前入口：{link(p,"CONTINUE_HERE.md")}；当前白皮书：{link(p,"docs/research/TWO_WAVE_WHITEPAPER.md")}。')
    return docs


def classify(relative: str, root: Path, documents: dict) -> str:
    if relative.startswith(('archive/', 'docs/archive/')):
        return 'archived_reference_not_current_authority'
    if relative in documents or relative == AUTHORITY or relative.startswith('docs/governance/'):
        return 'current_control_plane' if relative != 'docs/governance/source_closure_manifest.json' else 'frozen_seed_manifest'
    if relative.startswith('experiments/'):
        return 'historical_experiment_evidence_not_current_instruction'
    if relative.startswith('data/'):
        return 'frozen_development_data'
    if relative.startswith('tests/'):
        return 'maintained_regression_test'
    if relative == 'scripts/close_two_wave_v0707_governance.py':
        return 'retired_mutating_entrypoint_pure_snapshot_helpers_only'
    if relative.startswith('scripts/'):
        if relative in {'scripts/repository_consistency.py', 'scripts/validate_theme_package.py'}:
            return 'current_validation_tool'
        return 'retained_historical_replay_not_authorized_new_scoring'
    if relative.startswith('.github/'):
        return 'current_validation_workflow'
    if relative.startswith('.codex/'):
        return 'current_environment_setup_only'
    if relative.startswith('src/factor_lab/visual_structure/two_wave/'):
        return 'retained_research_component_not_runtime_winner'
    if relative.startswith(('src/', 'shared/', 'docs/ops/', 'docs/schemas/')):
        return 'frozen_foundation_dependency_or_contract'
    if relative.startswith('docs/research/'):
        return 'frozen_historical_protocol_or_checkpoint'
    if relative in {'pyproject.toml', '.gitignore'}:
        return 'current_package_configuration'
    raise ValueError(f'unclassified file: {relative}')


def inventory(root: Path, documents: dict[str, str]) -> dict:
    names = sorted(set(files(root)) | set(documents) | {INVENTORY})
    entries = []
    for name in names:
        status = classify(name, root, documents)
        content_hash = (None if name == INVENTORY else
                        hashlib.sha256(documents[name].encode()).hexdigest() if name in documents else digest(root/name))
        entries.append({'path': name, 'status': status, 'sha256': content_hash})
    return {'schema': 'two_wave_repository_component_inventory@1.0',
            'authority': AUTHORITY, 'inventory_self_hash': 'excluded_to_avoid_self_reference',
            'file_count': len(entries), 'status_counts': dict(sorted(Counter(x['status'] for x in entries).items())),
            'files': entries}


def validate_preservation(root: Path) -> dict:
    baseline = load(root, BASELINE)
    counts = Counter()
    for row in baseline['files']:
        p = safe_path(root, row['preserved_path'])
        if not p.is_file() or digest(p) != row['sha256']:
            raise ValueError(f'original evidence/source lost: {row["original_path"]}')
        counts[row['disposition']] += 1
    return dict(counts)


def check_links(root: Path) -> tuple[int, list[str]]:
    checked, errors = 0, []
    for relative in files(root):
        if not relative.endswith('.md') or relative.startswith(('archive/', 'docs/archive/')):
            continue
        text = re.sub(r'```.*?```', '', (root/relative).read_text(encoding='utf-8'), flags=re.S)
        for m in re.finditer(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', text):
            target = m.group(1).strip().split(' "')[0].strip('<>')
            u = urlsplit(target)
            if u.scheme or u.netloc or target.startswith('#'):
                continue
            checked += 1
            dest = (root/relative).parent / unquote(u.path)
            if not dest.resolve().is_relative_to(root.resolve()) or not dest.exists():
                errors.append(f'{relative}: {target}')
    return checked, errors


def check(root: Path) -> dict:
    verify_authority(root)
    preserved = validate_preservation(root)
    docs = render_documents(root)
    for path, expected in docs.items():
        if not (root/path).is_file() or (root/path).read_text(encoding='utf-8') != expected:
            raise ValueError(f'derived current documentation drift: {path}; run --write')
    actual = load(root, INVENTORY)
    if actual != inventory(root, docs):
        raise ValueError('component inventory drift; review files, then run --write')
    workflows = sorted(str(p.relative_to(root)) for p in (root/'.github/workflows').glob('*') if p.is_file())
    if workflows != ['.github/workflows/ci.yml'] or (root/workflows[0]).read_text() != CI_TEXT:
        raise ValueError('only the frozen read-only CI workflow may remain active')
    if (root/'.codex/skills').exists() and any((root/'.codex/skills').rglob('SKILL.md')):
        raise ValueError('retired automatic strategy skill reappeared')
    links, errors = check_links(root)
    if errors:
        raise ValueError('broken current links: ' + '; '.join(errors[:20]))
    parsed = 0
    for relative in files(root):
        if relative.endswith('.py'):
            ast.parse((root/relative).read_text(encoding='utf-8'), filename=relative)
            parsed += 1
    # Authority evidence references must exist, but archived snapshots keep their historical context.
    def refs(value):
        if isinstance(value, dict):
            for v in value.values():
                yield from refs(v)
        elif isinstance(value, list):
            for v in value:
                yield from refs(v)
        elif isinstance(value, str) and ' ' not in value and value.startswith(('docs/', 'experiments/', 'src/', 'scripts/', 'data/')):
            yield value
    for relative in refs(load(root, AUTHORITY)):
        if not safe_path(root, relative).exists():
            raise ValueError(f'missing authority evidence pointer: {relative}')
    return {'status': 'passed', 'scientific_revision': 'v0.7.8', 'scientific_recomputation': False,
            'file_count': actual['file_count'], 'python_files_parsed': parsed,
            'derived_documents_checked': len(docs), 'current_local_links_checked': links,
            'current_broken_local_links': 0, 'preserved_original_files': sum(preserved.values()),
            'preservation_dispositions': preserved, 'active_workflow_count': len(workflows),
            'morphology_acceptance': False, 'trade_authority': False, 'production_authority': False}


def write(root: Path) -> None:
    verify_authority(root)
    validate_preservation(root)
    docs = render_documents(root)
    for relative, text in docs.items():
        p = root/relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    (root/INVENTORY).write_text(json.dumps(inventory(root, docs), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--write', action='store_true')
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        if args.write:
            write(ROOT)
        print(json.dumps(check(ROOT), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, SyntaxError) as exc:
        print(f'repository consistency failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
