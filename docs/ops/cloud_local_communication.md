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
- 云端复核：`COMPLETED — Route M`
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

### 阻断原因（历史记录）

CL-002 当时按“connector 无法直接读取 parquet 二进制”交接。该表述后来由 DATA_AVAILABILITY 节修正：源数据并不缺失，真正问题是当时当前云端执行通道无法把二进制文件送入 Python runtime。

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

### 本地执行命令（历史）

```bash
python -m pip install -e . editables==0.6
python scripts/validate_theme_package.py
python -m pytest -q \
  tests/unit/test_market_state_tool_registry_v1_5.py \
  tests/unit/test_timing_infrastructure_four_layer_inventory.py \
  tests/unit/test_timing_layer2_measurement_boundary.py \
  tests/unit/test_timing_layer3_strategy_boundary.py \
  tests/unit/test_timing_layer3_orchestration.py \
  tests/unit/test_timing_strategy_identity_registry.py \
  tests/unit/test_two_wave_morphology_identity_v060.py
mkdir -p cloud_results/local_v060_qualified_identity_audit
python scripts/run_two_wave_qualified_identity_audit_v060.py \
  --output cloud_results/local_v060_qualified_identity_audit \
  | tee cloud_results/local_v060_qualified_identity_audit/run.log
```

### 本地已执行反馈（2026-09-06）

- status: `COMPLETED`
- Route candidate: `M`
- actual branch / commit: `codex/two-wave-phase1-20260905` / `a45a3a986df80228daa500af3c95e67c7f475ff5`
- frozen research diff check: exit 0；该区间仅有 `AGENTS.md` 与 `docs/ops/cloud_local_communication.md`
- Python / OS: Python 3.11.11 / Linux debian 7.1.8+deb13-amd64 x86_64 GNU/Linux
- five native 5m SHA256/bytes/row_count/date 全部匹配 manifest；未 resample；无 2021+
- `validate_theme_package.py`: exit 1，仅 `AGENTS.md` source-closure drift，不是 `IDENTITY_INPUT_DRIFT`
- focused pytest: **37 passed**, exit 0
- v0.6.0 runner: exit 0
- raw qualified counts: **734 / 691 / 691 / 721 / 746**
- canonical counts: **712 / 673 / 678 / 700 / 728**
- legacy-selected identities: **404 / 371 / 382 / 392 / 392**
- prefix checks: **15/15 passed**, confirmed rewrite count **0**
- all-qualified strict matches offset1..4: **180 / 129 / 129 / 184**
- main unmatched: **531 / 583 / 582 / 527**
- strict matches hidden by packing fraction: **60.56% / 58.14% / 57.36% / 56.52%**
- result directory: `cloud_results/local_v060_qualified_identity_audit/`
- any code change: none

### 云端正式复核

云端已完成 CL-002 复核并正式裁决 **Route M**：exclusive packing 必须保持 downstream，但 qualified financial identity 自身在 harmless 5m slicing 上仍 materially unstable。正式报告：`docs/research/two_wave_qualified_identity_results_v060.md`。

---

## DATA_AVAILABILITY — 禁止再因 parquet 二进制把计算甩回本地

> 本节由本地在 CL-20260906-002 完成后核对 GitHub 远程字节得出。不是新的研究裁决。

远程 `staryocean0/factorlab-two-wave-strategy-lab` 的 `codex/two-wave-phase1-20260905` 已经跟踪全部 development parquet，无 Git LFS。CL-002 所需五个 native 5m views 合计约 16.3MB，源数据差额为 0 bytes。

云端不得再把“不能文本预览 parquet”本身写成缺数据。允许 handoff 只有：

1. 所需 repo path 实际缺失 / hash 不一致；或
2. 当前云端会话对冻结命令发生了**真实执行失败**，并记录 traceback / exit code。

---

## CL-20260906-003 — v0.6.1 unmatched-identity decomposition 五视图正式审计

### 状态

- 云端预分析：`COMPLETED`
- 冻结协议：`COMPLETED`
- evaluator 实现：`COMPLETED`
- 云端 helper 级验证：`COMPLETED`
- 云端真实 repo/parquet replay：`BLOCKED_BY_RUNTIME_NETWORK`
- 本地执行：`WAITING_LOCAL_EXECUTION`
- 云端结果复核：`pending`
- 总体状态：`morphology_replication_not_yet_accepted`
- operational baseline：仍为 `v0.4.3`

### 任务目标

v0.6.0 Route M 已证明 packing 不是唯一问题。本任务不修模型，只回答：

> 对 offset0 中未进入 v0.6.0 mutual-unique strict match 的 qualified financial identities，最早在哪个既有 upstream layer 丢失 harmless-offset counterpart？

按冻结层级依次检查：

1. qualified strict edge 存在但非 mutual-unique；
2. all-evaluated raw identity 的 phase mismatch / qualification survival；
3. filtered exact-ridge tuple birth；
4. same birth-level 五个 filtered extrema 是否全部唯一存活；
5. 是否仅 birth-scale path 迁移；
6. filtered extrema 本身是否无法稳定存活。

session boundary 与 local-envelope nearest displacement 都只作 overlay diagnostic，绝不改变 matcher。

### 冻结研究身份

- Repository: `staryocean0/factorlab-two-wave-strategy-lab`
- Branch: `codex/two-wave-phase1-20260905`
- v0.6.1 frozen implementation commit: **`bda82c29103080f69f36d7848b40216088895b3a`**
- 后续如只有本沟通文档/PR/CONTINUE_HERE 变化，不视为研究实现漂移。

必须先读：

1. `docs/research/two_wave_unmatched_identity_decomposition_preanalysis_v061.md`
2. `docs/research/two_wave_unmatched_identity_decomposition_protocol_v061.md`
3. `src/factor_lab/visual_structure/two_wave/unmatched_identity_decomposition_v061.py`
4. `scripts/run_two_wave_unmatched_identity_decomposition_v061.py`
5. `tests/unit/test_two_wave_unmatched_identity_decomposition_v061.py`
6. `docs/research/two_wave_qualified_identity_results_v060.md`

### 云端已完成事项

云端在看到任何 v0.6.1 decomposition 数字前已经：

- 写完 v0.6.1 preanalysis；
- 冻结 attribution order 和所有 stage 定义；
- 实现 evaluator-only helper / runner；
- 未改 v0.5.2 ridge linking、v0.5.4 qualification、v0.6.0 matcher、D1/D2/PAWCT、packing 或 outcome；
- 对新增 Python 文件完成 `py_compile`；
- 在隔离 synthetic package 上跑新增 helper tests：**9/9 PASS**；
- 对 indexed edge graph 做 50 random seeds × phase-aware/phase-ignored = **100/100** 与 brute-force strict definition 逐边等价检查；
- 发现 v0.5.2 每视图约 36k–38k evaluated/tuple births 后，将 evaluator 的边枚举改为第一锚点 `±5m` 索引窗口。该索引只利用合法 strict edge 的必要条件，因此不改变边集合；确定性单测已固定其与 brute-force 定义一致。

### 云端真实执行失败证据

这次 handoff **不是**因为“parquet 是二进制”。云端已经按最新 `AGENTS.md` 真正尝试执行：

1. GitHub blob 直取 `5m_offset_0.parquet`：失败，connector 抛出

```text
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb5 in position 19
```

2. 当前 container 直接 clone public repo：

```bash
git clone --branch codex/two-wave-phase1-20260905 --single-branch \
  https://github.com/staryocean0/factorlab-two-wave-strategy-lab.git \
  /tmp/factorlab-two-wave-strategy-lab
```

实际结果：exit **128**

```text
fatal: unable to access 'https://github.com/staryocean0/factorlab-two-wave-strategy-lab.git/':
Could not resolve host: github.com
```

因此当前 cloud runtime 的阻断是**网络/DNS + binary connector transport**，不是 repo 源数据缺失。符合 DATA_AVAILABILITY 允许本地 handoff 的第 2 条。

### 本地不得改变的冻结口径

- five raw/filtered anchors 全部位置对应；
- 每个绝对 timestamp delta `<= 5 minutes`；
- mutual-unique only；
- phase-ignored relation 只用于诊断 phase mismatch；
- 不允许 nearest/best tie-break；
- `first_record_id` 是 canonical identity 唯一允许的 causal upstream representative；
- 不改 sigma schedule、ridge linking、tuple-birth death certification、qualification thresholds、packing；
- 不用 D1/D2/PAWCT/return/outcome 做 matching 或 category selection；
- 不新增 2021+、不 resample。

### 本地执行前 research diff 检查

允许当前分支 HEAD 高于 frozen implementation commit，但必须证明此后研究文件没有被改动：

```bash
git checkout codex/two-wave-phase1-20260905
git pull --ff-only
git rev-parse HEAD
git status --short

git diff --exit-code \
  bda82c29103080f69f36d7848b40216088895b3a..HEAD -- \
  src tests scripts docs/research data pyproject.toml
```

最后一条必须 exit 0。如果非 0，停止并报告，不在漂移版本上跑 formal replay。

### 测试

```bash
python -m pip install -e . editables==0.6
python scripts/validate_theme_package.py

python -m pytest -q \
  tests/unit/test_market_state_tool_registry_v1_5.py \
  tests/unit/test_timing_infrastructure_four_layer_inventory.py \
  tests/unit/test_timing_layer2_measurement_boundary.py \
  tests/unit/test_timing_layer3_strategy_boundary.py \
  tests/unit/test_timing_layer3_orchestration.py \
  tests/unit/test_timing_strategy_identity_registry.py \
  tests/unit/test_two_wave_morphology_identity_v060.py \
  tests/unit/test_two_wave_unmatched_identity_decomposition_v061.py
```

记录 package-validation 的真实结果。若仍只因 `AGENTS.md` source closure drift 而 exit 1，可记录但不得伪装为 pass；decisive gate 是 research diff、tests、v0.6.0 controls 与 v0.6.1 accounting 全部闭合。

### 正式 runner

```bash
mkdir -p cloud_results/local_v061_unmatched_identity_decomposition

python scripts/run_two_wave_unmatched_identity_decomposition_v061.py \
  --output cloud_results/local_v061_unmatched_identity_decomposition \
  | tee cloud_results/local_v061_unmatched_identity_decomposition/run.log
```

若 runner 存在真实机械 bug：

- 先保存 traceback/exit code；
- 不改 frozen protocol/category order/tolerance；
- 只有当修复行为由冻结 protocol 唯一决定时，才允许做最小实现修复并加测试，同时单独提交；
- 否则停止并反馈云端，不自行重新设计实验。

### 必须复现的硬 checkpoints

raw qualified counts：

```text
734 / 691 / 691 / 721 / 746
```

main canonical qualified count：`712`

v0.6.0 controls：

```text
offset1: matches=180, ambiguous_main/other=1/1, unmatched_main/other=531/492
offset2: matches=129, ambiguous_main/other=0/0, unmatched_main/other=583/549
offset3: matches=129, ambiguous_main/other=1/0, unmatched_main/other=582/571
offset4: matches=184, ambiguous_main/other=1/1, unmatched_main/other=527/543
```

runner 已内置断言。任何一项不一致，视为 `IDENTITY_INPUT_DRIFT` 或 implementation drift，不解释 decomposition。

### 必须生成的产物

```text
cloud_results/local_v061_unmatched_identity_decomposition/summary.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_1.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_2.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_3.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_4.json
cloud_results/local_v061_unmatched_identity_decomposition/data_identity.json
cloud_results/local_v061_unmatched_identity_decomposition/run.log
```

不要重复上传 parquet。

### 本地必须回报

#### 本地反馈 — CL-20260906-003

- status: COMPLETED / FAILED / BLOCKED
- actual branch / commit:
- frozen research diff exit code:
- Python / OS:
- git status:
- package validation result:
- pytest pass count / exit code:
- runner exit code:
- data SHA / rows / date / manifest status:
- qualified counts offset0..4:
- canonical counts offset0..4:
- v0.6.0 controls reproduced: yes/no
- attribution denominator per offset:
- attribution counts/fractions per offset:
- `qualification_survival_loss` rejection reason counts:
- `post_tuple_birth_loss` projection/evaluate diagnostics:
- same-level unique-anchor-count distributions:
- max-any-level unique-anchor-count distributions:
- session-boundary prevalence by category + strict matched control:
- local-envelope candidate-count / min-max-delta distributions:
- accounting closure: matched + ambiguous + exactly-one attribution = main canonical count, per offset yes/no
- result directory / summary / details / data_identity / run.log:
- failures / unverified items:
- any code change + commit (if any):

本地**不要**根据 attribution 数字直接修改 ridge/qualification/matcher。最终“下一层该修哪里”由云端复核后再单独冻结 repair experiment。
