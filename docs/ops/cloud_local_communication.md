# 云端—本地沟通记录

> 本文按仓库 `AGENTS.md` 的“云端—本地交接协议”维护。当前协作协议已由用户明确启用。
>
> Protocol 2 当前执行优先级：云端当前会话可执行 → 本地大模型 → GitHub Actions。用户已明确告知 Actions 当前无可用额度，因此不得为本任务启动、重跑或用 push 试探 Actions。

---

## CL-20260906-001 — 历史误交接：v0.5.2 formal six-view

### 状态

**SUPERSEDED / DO NOT EXECUTE**

该任务由云端误把历史 run `33973525292` 当成当前断点而生成。v0.5.2 后来已由后续拆分证据闭合，不是当前待执行任务。保留编号仅用于审计，不得本地重跑或据此回退研究前沿。

---

## CL-20260906-002 — v0.6.0 qualified financial identity 五视图本地正式审计

### 状态

- 云端诊断：`handoff_required`
- 本地执行：`COMPLETED`
- 本地 Route candidate：`M`（非正式裁决；最终 Q/U/M 由云端复核）
- 云端复核：`pending`
- 总体状态：`morphology_replication_not_yet_accepted`
- operational baseline：仍为 `v0.4.3`

### 当前真实研究问题

冻结上游仍是：

> **v0.5.2 exact-ridge parent identity + v0.5.4 full-cycle qualification**

v0.5.9 已证明此前 direction/PAWCT 的大量跨 slicing disagreement 混入了**不同 selected financial events 被拿来互相比**的 identity confound。v0.6.0 因此先把 morphology identity 从 legacy exclusive packing 中拆开。

本任务只回答：

> 在五个 supplied native 5m views 上，**canonical qualified financial identities** 是否已经形成清晰、低歧义的 mutual-unique same-event 结构，并且相对 legacy selected-only identity 明显更完整？

如果 qualified pool 本身稳定、而 legacy selected 丢掉大量 stable identities，则 packing 是主要污染源（Route Q）。如果 qualified pool 自身仍大面积 absent/ambiguous，则继续 upstream identity（Route U）。如果 packing 确实隐藏大量稳定 identity、但 qualified pool 仍有实质不稳定，则 Route M。

**本任务不是 direction-model POC。禁止调 D1/D2/PAWCT，禁止 H1/H2、第三浪、收益/P&L、交易、OOS、paper trading 或 production。**

### 冻结研究身份

- Repository：`staryocean0/factorlab-two-wave-strategy-lab`
- Branch：`codex/two-wave-phase1-20260905`
- 冻结研究实现/当前 v0.6.0 partial-evidence commit：`4643133f518299d6710f3c1cc01b6399b9482c31`

后续已知提交仅涉及 `AGENTS.md` 与本沟通文档。执行前二选一：

#### A. 当前分支执行，先证明研究文件未漂移

```bash
git checkout codex/two-wave-phase1-20260905
git rev-parse HEAD
git status --short

git diff --exit-code \
  4643133f518299d6710f3c1cc01b6399b9482c31..HEAD -- \
  src tests scripts docs/research data pyproject.toml
```

最后一条必须 exit 0。

#### B. 使用冻结 worktree

```bash
git worktree add ../two-wave-v060-local 4643133f518299d6710f3c1cc01b6399b9482c31
cd ../two-wave-v060-local
```

不得为了结果更好而修改 frozen research files。

### 必须先读

1. `AGENTS.md`
2. `CONTINUE_HERE.md`
3. `docs/research/two_wave_qualified_identity_audit_protocol_v060.md`
4. `docs/research/two_wave_qualified_identity_partial_results_v060.md`
5. `src/factor_lab/visual_structure/two_wave/morphology_identity_v060.py`
6. `scripts/run_two_wave_qualified_identity_audit_v060.py`
7. `tests/unit/test_two_wave_morphology_identity_v060.py`

### 冻结 identity 定义

单视图 canonical financial identity：

```text
(start_phase, five raw occurrence bars)
```

同五 anchors 在不同 birth scale 出现，只是同一 identity 的后续 scale evidence；不得重复发布金融 identity，也不得改写首次发布事件。

Cross-view strict identity edge **只有以下三个条件**：

1. start phase 相同；
2. ordered five occurrence timestamps 逐位置比较；
3. 五个绝对 timestamp delta 全部 `<= 5 minutes`（one nominal 5m bar）。

然后只接受 **mutual-unique** edge。

- 多匹配必须记 ambiguity；
- 禁止 nearest/best post-hoc tie-break；
- **没有** scale-class 条件；
- **没有** span-ratio 条件；
- interval IoU、D1、D2、PAWCT、amplitude、return、outcome 都不得参与 identity match。

### 云端已确认的 partial evidence

冻结 v0.5.4 qualified input 五视图统计：

| view | qualified records | legacy selected | packing suppressed |
|---|---:|---:|---:|
| 5m_offset_0 | 734 | 404 | 330 |
| 5m_offset_1 | 691 | 371 | 320 |
| 5m_offset_2 | 691 | 382 | 309 |
| 5m_offset_3 | 721 | 392 | 329 |
| 5m_offset_4 | 746 | 392 | 354 |

平均约 45.81% qualified observations 被 legacy non-overlap packing 抑制。

main `5m_offset_0` 已由真实 734 qualified records 直接复现：

- 734 qualified records → **712 canonical identities**；
- 21 个 same-anchor duplicate-scale groups / 43 records；
- 404 canonical identities 有 legacy-selected member；
- **308（43.2584%）canonical qualified identities 被 legacy packing 完全隐藏**；
- same-anchor D1 / direction geometry 冲突为 0。

历史 v0.5.4 upstream native-5m prefix 已是 15/15 zero rewrite，但 v0.6.0 新 identity-event append-only stream 仍要求本地 runner 自己完成 15 个 prefix checks。

selected-only strict same-event 诊断已有强信号，但不足以裁决 Route Q/U/M；缺口正是 offsets1..4 的完整 qualified bodies。

### 阻断原因

当前云端会话无法读取仓库 parquet 二进制；历史 artifacts 又没有序列化 offset1..4 的完整 qualified record bodies。用户已要求不再消耗 Actions。

所以本地模型需要做的不是重新设计算法，而是**直接执行仓库已有的冻结 local-only runner**。

### 最小数据

必须使用仓库已经供应的：

```text
data/development/5m_offset_0.parquet
data/development/5m_offset_1.parquet
data/development/5m_offset_2.parquet
data/development/5m_offset_3.parquet
data/development/5m_offset_4.parquet
data/manifest.json
```

边界：

- `000852.SH` CSI1000 index signal data；
- 2015-01-05 至 2020-12-31；
- supplied DataHub-built views only；
- 禁止本地重新 resample；
- 不需要 `1m_official`；
- 禁止下载/推断/补造 2021+ 数据。

大数据留在本地。建议记录每个 parquet 的 SHA256、bar count、min/max trading day 和 manifest validation 状态。

### 本地执行命令

#### 1. 安装与 package validation

```bash
python -m pip install -e . editables==0.6
python scripts/validate_theme_package.py
```

记录 exit codes。

#### 2. AGENTS 最低治理测试 + v0.6.0 identity tests

```bash
python -m pytest -q \
  tests/unit/test_market_state_tool_registry_v1_5.py \
  tests/unit/test_timing_infrastructure_four_layer_inventory.py \
  tests/unit/test_timing_layer2_measurement_boundary.py \
  tests/unit/test_timing_layer3_strategy_boundary.py \
  tests/unit/test_timing_layer3_orchestration.py \
  tests/unit/test_timing_strategy_identity_registry.py \
  tests/unit/test_two_wave_morphology_identity_v060.py
```

资源足够可附加 full `pytest -q`，但不是 decisive gate 的替代。

#### 3. 直接执行冻结 v0.6.0 local-only runner

```bash
mkdir -p cloud_results/local_v060_qualified_identity_audit

python scripts/run_two_wave_qualified_identity_audit_v060.py \
  --output cloud_results/local_v060_qualified_identity_audit \
  | tee cloud_results/local_v060_qualified_identity_audit/run.log
```

**不要另写 matching 算法，除非该脚本本身存在真实执行 bug。** 若存在 bug，先停止并报告；不得静默改 protocol/threshold/matching relation。

该 runner 已经会：

- 加载 `5m_offset_0..4`；
- 构建 frozen v0.5.4 qualified streams；
- canonicalize qualified records；
- 发布 causal immutable identity + append-only scale evidence；
- 对五个 views 各跑 25%/50%/75% prefix，共 **15 checks**；
- offset0 vs offset1..4 做 all-qualified mutual-unique strict matches；
- 同时做 legacy-selected mutual-unique strict matches；
- 输出 ambiguity / unmatched；
- 统计 strict qualified matches 中有多少被 legacy packing 隐藏；
- D1 agreement 只作为 strict-identity-match 后的 diagnostic，不参与 matching。

### 必须先通过的 identity checkpoints

runner 的 raw qualified counts 应复现：

```text
5m_offset_0: 734
5m_offset_1: 691
5m_offset_2: 691
5m_offset_3: 721
5m_offset_4: 746
```

main canonical count 应复现 **712**。

如果 raw counts 不一致：

- 不继续解释 Route Q/U/M；
- 标记 `IDENTITY_INPUT_DRIFT`；
- 报实际 commit、数据身份、counts 与日志；
- 不调参数追预期。

### 必须保留的输出

runner 默认会生成：

```text
cloud_results/local_v060_qualified_identity_audit/summary.json
cloud_results/local_v060_qualified_identity_audit/5m_offset_0/canonical_qualified_identities.json
cloud_results/local_v060_qualified_identity_audit/5m_offset_0/causal_identity_events.json
cloud_results/local_v060_qualified_identity_audit/5m_offset_0/identity_evidence_events.json
... offsets1..4 同类文件
cloud_results/local_v060_qualified_identity_audit/run.log
```

请另外生成一个小型 `data_identity.json`（SHA256/bar count/date range/manifest status 即可）。

不要上传原始 parquet 或巨型中间数据。

### 本地必须回报的 decisive metrics

从 `summary.json` 逐 offset（offset0 vs offset1..4）报告两套：

#### canonical qualified identities

- main events / other events
- mutual_unique_matches
- main_match_fraction
- other_match_fraction
- ambiguous_main / ambiguous_other
- unmatched_main / unmatched_other
- matches_hidden_by_legacy_packing
- hidden_match_fraction
- D1_same_label_fraction_on_strict_identity_matches（仅 diagnostic）

#### legacy selected identities

- main events / other events
- mutual_unique_matches
- main_match_fraction
- other_match_fraction
- ambiguous_main / ambiguous_other
- unmatched_main / unmatched_other

另外必须报告：

- 五个 view 的 qualified record count；
- canonical qualified identity count；
- legacy selected identity count；
- duplicate scale groups；
- overlap-component diagnostics；
- **15/15 identity prefix checks 是否全部 passed、confirmed_rewrite_count 是否为 0。**

### Frozen route interpretation

本 protocol **没有事后数值 cutoff**，不得执行后再发明百分比阈值。

只按已冻结语义报告：

- **Route Q — qualified identity adequate**：canonical qualified identities 在四个 offsets 都显示清晰、低歧义的 mutual-unique local-match 结构，而且 materially stronger than legacy selected-only；packing 隐藏了大量 stable strict identities。然后才允许回到 strict same-event matched set 上做 direction adjudication。
- **Route U — upstream identity still unstable**：canonical qualified identities 本身仍大面积 absent/ambiguous；此时禁止再碰 direction，应回到 ridge/qualification identity。
- **Route M — mixed**：packing 确实隐藏 substantial stable identities，但 qualified identity 仍 materially unstable；packing 保持 downstream，同时继续 upstream identity research。

本地模型可以给出 `Route Q/U/M candidate` 与理由，但**最终研究裁决由云端收到结果后复核**。

无论哪条 route，总体状态仍是 `morphology_replication_not_yet_accepted`。

### 本地反馈模板

```markdown
#### 本地反馈 — CL-20260906-002

- status: COMPLETED / FAILED / BLOCKED
- Route candidate: Q / U / M / UNDECIDABLE
- actual branch / commit:
- frozen research diff check + exit code:
- Python / OS:
- git status:

- data files + SHA256:
- per-view bar count:
- min/max trading date:
- manifest validation:

- package validation command + exit code:
- pytest command + pass count + exit code:
- v0.6.0 runner command + exit code:

- raw qualified counts offset0..4:
- canonical counts offset0..4:
- legacy-selected identity counts offset0..4:
- duplicate-scale groups offset0..4:
- overlap components summary:

- prefix checks: passed / 15:
- confirmed rewrite count:

- offset0-vs-offset1 qualified metrics:
- offset0-vs-offset1 legacy-selected metrics:
- offset0-vs-offset2 qualified metrics:
- offset0-vs-offset2 legacy-selected metrics:
- offset0-vs-offset3 qualified metrics:
- offset0-vs-offset3 legacy-selected metrics:
- offset0-vs-offset4 qualified metrics:
- offset0-vs-offset4 legacy-selected metrics:

- strict matches hidden by packing / hidden fraction per offset:
- ambiguity/unmatched interpretation:
- Route candidate rationale:

- result directory:
- summary.json:
- data_identity.json:
- run.log:
- failures / unverified items:
- any code change: 若有，附 diff/commit；不得把修改后的 protocol 当冻结 protocol
```

### 云端收到本地反馈后的动作

1. 明确标记“本地已执行”与“云端已复核”的边界；
2. 复核 code/data identity、raw qualified checkpoints、15/15 prefix、mutual-unique helper 口径与 summary；
3. 按 frozen Q/U/M 语义完成正式 v0.6.0 adjudication；
4. 更新 v0.6.0 results、`CONTINUE_HERE.md`、Issue/PR 前沿；
5. 只有 Route Q 才回到 **strict same-event pairs** 上重新 adjudicate direction/PAWCT；
6. Route U/M 均不得通过调 direction 来逃避 identity 问题；
7. PR 保持 Draft，不 merge main；不进入 H1/H2、收益或交易。


### 本地已执行反馈（2026-09-06，填写 CL-002 模板）

#### 本地反馈 — CL-20260906-002

- status: COMPLETED
- Route candidate: M
- actual branch / commit: `codex/two-wave-phase1-20260905` / `a45a3a986df80228daa500af3c95e67c7f475ff5`
- frozen research diff check + exit code: `git diff --exit-code 4643133f518299d6710f3c1cc01b6399b9482c31..HEAD -- src tests scripts docs/research data pyproject.toml` → exit 0。该区间仅有 `AGENTS.md` 与 `docs/ops/cloud_local_communication.md`。
- Python / OS: Python 3.11.11 / Linux debian 7.1.8+deb13-amd64 x86_64 GNU/Linux
- git status: 执行时干净；本反馈提交前仅新增 `cloud_results/local_v060_qualified_identity_audit/` 与本段沟通记录。

- data files + SHA256:
  - `data/development/5m_offset_0.parquet` 3351411 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`
  - `data/development/5m_offset_1.parquet` 3226743 `4523615193c177dda2f63a69dd32a2d21e2b15c78283de2d242dd6cd695fc284`
  - `data/development/5m_offset_2.parquet` 3223863 `737548b04ca93fdbfafda806c5f98051b0521e868d71bcab00f23c062ef8ee82`
  - `data/development/5m_offset_3.parquet` 3225315 `20a8a4aba19f60946e5781947f658d0b16a2d8758e6318b43c0a0ececdd09282`
  - `data/development/5m_offset_4.parquet` 3227705 `ceba69dce07223ba92204dc4994991eeabcaf62aacfb9869fd9403da43694b1b`
  - `data/manifest.json` 6185 `b40b352a4940c7cf475150a63af135fb3e92bd2061f9d631c0fc2032b4294291`
- per-view bar count: 70114 / 67192 / 67192 / 67193 / 67191
- min/max trading date: 2015-01-05 / 2020-12-31（五视图一致）
- manifest validation: 五个 native 5m views 的 SHA256、bytes、row_count、日期全部匹配 `data/manifest.json`。runner 内 `manifest_verified=true`。未使用 `1m_official`，未本地 resample，无 2021+ 行。

- package validation command + exit code: `.venv/bin/python scripts/validate_theme_package.py` → exit 1。失败原因仅 `frozen source drifted: AGENTS.md`（handoff 协议后续提交）。研究文件相对冻结 commit `4643133` 无漂移。**不是** `IDENTITY_INPUT_DRIFT`。
- pytest command + pass count + exit code: `.venv/bin/python -m pytest -q tests/unit/test_market_state_tool_registry_v1_5.py tests/unit/test_timing_infrastructure_four_layer_inventory.py tests/unit/test_timing_layer2_measurement_boundary.py tests/unit/test_timing_layer3_strategy_boundary.py tests/unit/test_timing_layer3_orchestration.py tests/unit/test_timing_strategy_identity_registry.py tests/unit/test_two_wave_morphology_identity_v060.py` → **37 passed**, exit 0。
- v0.6.0 runner command + exit code: `.venv/bin/python scripts/run_two_wave_qualified_identity_audit_v060.py --output cloud_results/local_v060_qualified_identity_audit | tee cloud_results/local_v060_qualified_identity_audit/run.log` → exit 0。未改 runner / matching relation / threshold / offset。未开 v0.6.1。

- raw qualified counts offset0..4: **734 / 691 / 691 / 721 / 746**（与冻结 checkpoint 完全一致）
- canonical counts offset0..4: **712 / 673 / 678 / 700 / 728**（main canonical **712** 复现）
- legacy-selected identity counts offset0..4: **404 / 371 / 382 / 392 / 392**
- duplicate-scale groups offset0..4: **21 / 17 / 13 / 21 / 18**
- overlap components summary:
  - offset0: components=356, nontrivial=176, size median/p90/p95/p99/max=1/4/5/7/10, span median/p90/max bars=48/96/166
  - offset1: components=328, nontrivial=164, size 2/4/5/7/9, span 50/93/186
  - offset2: components=338, nontrivial=164, size 1/4/5/7/8, span 49/93/207
  - offset3: components=344, nontrivial=173, size 2/4/5/7/8, span 49/99/159
  - offset4: components=338, nontrivial=177, size 2/4/5/7/12, span 52/96/202

- prefix checks: **15 / 15 passed**
- confirmed rewrite count: **0**（全部 15 项均为 0；`prefix_zero_rewrite_count=15`）

- offset0-vs-offset1 qualified metrics: main/other events 712/673; mutual_unique_matches 180; main_match_fraction 0.25280898876404495; other_match_fraction 0.2674591381872214; ambiguous_main/other 1/1; unmatched_main/other 531/492; matches_hidden_by_legacy_packing 109; hidden_match_fraction 0.6055555555555555; D1_same_label_fraction_on_strict_identity_matches 0.9666666666666667（diagnostic only）
- offset0-vs-offset1 legacy-selected metrics: main/other 404/371; mutual_unique_matches 72; main_match_fraction 0.1782178217821782; other_match_fraction 0.1940700808625337; ambiguous 0/0; unmatched 332/299
- offset0-vs-offset2 qualified metrics: 712/678; matches 129; main 0.18117977528089887; other 0.1902654867256637; ambiguous 0/0; unmatched 583/549; hidden 75; hidden_fraction 0.5813953488372093; D1 0.9689922480620154
- offset0-vs-offset2 legacy-selected metrics: 404/382; matches 54; main 0.13366336633663367; other 0.14136125654450263; ambiguous 0/0; unmatched 350/328
- offset0-vs-offset3 qualified metrics: 712/700; matches 129; main 0.18117977528089887; other 0.18428571428571427; ambiguous 1/0; unmatched 582/571; hidden 74; hidden_fraction 0.5736434108527132; D1 0.9612403100775194
- offset0-vs-offset3 legacy-selected metrics: 404/392; matches 55; main 0.13613861386138615; other 0.14030612244897958; ambiguous 0/0; unmatched 349/337
- offset0-vs-offset4 qualified metrics: 712/728; matches 184; main 0.25842696629213485; other 0.25274725274725274; ambiguous 1/1; unmatched 527/543; hidden 104; hidden_fraction 0.5652173913043478; D1 0.9510869565217391
- offset0-vs-offset4 legacy-selected metrics: 404/392; matches 81; main 0.2004950495049505; other 0.2066326530612245; ambiguous 0/0; unmatched 323/311

- strict matches hidden by packing / hidden fraction per offset: 109 / 0.6055555555555555; 75 / 0.5813953488372093; 74 / 0.5736434108527132; 104 / 0.5652173913043478
- ambiguity/unmatched interpretation: 歧义几乎不存在（每对最多 1 个 ambiguous identity），失败模式不是 multi-match tie。四个 offset 上 mutual-unique matches 都存在，且都明显多于 legacy selected-only（180/129/129/184 vs 72/54/55/81）。但 unmatched 在四个 offset 都是主体（main unmatched 531/583/582/527）。因此 qualified pool 并没有形成“清晰覆盖”的 same-event 结构。packing 同时把已经存在的 strict matches 隐藏了一半以上。未发明事后百分比 cutoff，也未挑选“最好”的 offset。
- Route candidate rationale: 按冻结语义报 **Route M**。packing 确实隐藏了大量已经形成的 strict same-event identities，应保持 downstream；但 canonical qualified identities 在四个 harmless native 5m offset 上仍大面积 unmatched，不能称为 Route Q 所要求的清晰低歧义覆盖，也不应把问题收缩成只改 packing 后立刻回到 direction。本地不裁决、不重开 v0.5.2/v0.5.4、不调 D1/D2/PAWCT、不开 v0.6.1。最终 Q/U/M 由云端复核。

- result directory: `cloud_results/local_v060_qualified_identity_audit/`
- summary.json: `cloud_results/local_v060_qualified_identity_audit/summary.json` SHA256 `04fe6fd51eb0168414624c5b8d69925f12e64bc92c43ef6849d4b68a47f127ba`
- data_identity.json: `cloud_results/local_v060_qualified_identity_audit/data_identity.json`
- run.log: `cloud_results/local_v060_qualified_identity_audit/run.log`（与 summary.json 字节相同；因 `*.log` gitignore，提交时 `git add -f`）
- failures / unverified items:
  - `scripts/validate_theme_package.py` exit 1，仅 AGENTS.md source-closure drift；
  - 未跑 full `pytest -q`（协议写明不是 decisive gate 替代）；
  - 未做云端复核，不得把本反馈写成云端独立全量复验或正式 v0.6.0 adjudication；
  - 全局状态仍为 `morphology_replication_not_yet_accepted`。
- any code change: 无。未修改 src/tests/scripts/docs/research/data/pyproject.toml。仅新增本审计产物与本沟通反馈。
