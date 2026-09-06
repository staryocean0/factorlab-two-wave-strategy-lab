# 云端—本地沟通记录

> 本文按仓库 `AGENTS.md` 的“云端—本地交接协议”维护。当前协作协议已由用户明确启用。
>
> 执行优先级按 Protocol 2：云端当前会话可执行 → 本地大模型 → GitHub Actions。用户已明确告知 Actions 当前无可用额度，因此本记录中的本地任务不得改派、重跑或用 push 试探 Actions。

---

## CL-20260906-001 — 历史误交接：v0.5.2 formal six-view

### 状态

- **SUPERSEDED / DO NOT EXECUTE**
- 原因：云端曾误把历史 Actions run `33973525292` 当成当前研究断点。该 v0.5.2 六视图问题后来早已由拆分的 five-view + 1m 正式证据闭合，不是当前待执行任务。
- 本任务不得在本地重跑，也不得据此回退当前研究前沿。
- 保留此编号仅用于审计错误交接历史。

当前真实研究前沿以 `CONTINUE_HERE.md`、`docs/research/two_wave_qualified_identity_audit_protocol_v060.md` 与下面 `CL-20260906-002` 为准。

---

## CL-20260906-002 — v0.6.0 all-qualified 五视图 parent-identity 审计

### 状态

- 云端诊断：`handoff_required`
- 本地执行：`WAITING_LOCAL_EXECUTION`
- 云端复核：`pending`
- 总体形态权限：仍为 `morphology_replication_not_yet_accepted`
- 禁止事项：D3 调参、H1/H2、第三浪、收益/P&L、交易、OOS、paper trading、production 均不得开启。

### 任务目标

在拥有完整冻结 development parquet 的本地环境，完成 **v0.6.0 minimal all-qualified five-view identity audit**。

需要回答的唯一研究问题：

> v0.6.0 对 qualified-parent identity 的修复，在**整个 qualified universe**（不是 selected-only 子集）上，是否真的提高了 native 5m offsets 之间的稳定父结构对齐，并且这种提高不是靠把唯一匹配转化为 ambiguous multiple matches 获得？

本任务只解决 identity gate。**不要重跑 1m，不要重算或调整 D3，不要引入新的 recognizer。**

### 冻结研究身份

- Repository：`staryocean0/factorlab-two-wave-strategy-lab`
- Branch：`codex/two-wave-phase1-20260905`
- 冻结研究实现 commit：`4643133f518299d6710f3c1cc01b6399b9482c31`

其后的已知提交只涉及 `AGENTS.md` 与云端—本地沟通文档，不应改变本任务的 `src/ tests/ scripts/ docs/research/ data/ pyproject.toml` 研究实现。

执行前必须采用下列两种方式之一。

**方式 A：当前分支执行，但先证明研究实现未漂移**

```bash
git checkout codex/two-wave-phase1-20260905
git rev-parse HEAD
git status --short

git diff --exit-code \
  4643133f518299d6710f3c1cc01b6399b9482c31..HEAD -- \
  src tests scripts docs/research data pyproject.toml
```

上述 `git diff --exit-code` 必须 exit 0。

**方式 B：创建独立 worktree / detached worktree，直接在冻结 commit 执行**

```bash
git worktree add ../two-wave-v060-local 4643133f518299d6710f3c1cc01b6399b9482c31
cd ../two-wave-v060-local
```

若发现 frozen research files 已发生实质变化，停止并报告，不自行选择“更合理”的版本。

### 冻结协议与可复用实现

必须先阅读：

1. `AGENTS.md`
2. `CONTINUE_HERE.md`
3. `docs/research/two_wave_qualified_identity_audit_protocol_v060.md`
4. `docs/research/two_wave_qualified_identity_partial_results_v060.md`
5. `scripts/run_two_wave_qualified_identity_audit_v060.py`
6. `src/factor_lab/visual_structure/two_wave/morphology_identity_v060.py`
7. `tests/unit/test_two_wave_morphology_identity_v060.py`
8. `scripts/run_two_wave_identity_v060_selected_only.py`

上游继续冻结：

- v0.5.2 exact-ridge parent identity
- v0.5.4 full-cycle-scale qualification
- v0.5.9 whole-curve direction

本任务不得改这些定义。

### 云端已有证据

v0.6.0 formal run `34013160799` 的五个 native 5m full views 已经完成，已有 qualified 计数：

| view | qualified | margin | range-like |
|---|---:|---:|---:|
| 5m_offset_0 | 734 | 727 | 7 |
| 5m_offset_1 | 717 | 714 | 3 |
| 5m_offset_2 | 708 | 706 | 2 |
| 5m_offset_3 | 691 | 689 | 2 |
| 5m_offset_4 | 688 | 683 | 5 |

五个 view 均应保持 `eligible_for_label_agreement=true`。

selected-only 已有证据：

- total main-side comparison pairs：1259
- v0.5.8：strict unique 57.665%；ambiguous 12.232%；only-main-owned 20.571%
- v0.6.0：strict unique 61.239%；ambiguous 12.470%；only-main-owned 16.918%
- selected-only delta：strict unique **+3.574pp**；only-main-owned **-3.653pp**；ambiguous **+0.238pp**

这些 selected-only 数字只说明改善方向，**不能替代 all-qualified verdict**。

当前云端阻断原因不是数学失败，而是：历史 artifacts 对 `5m_offset_1..4` 只保存了 qualified count/digest，没有保存完整 `qualified_records` bodies；云端当前又不能读取仓库内 parquet 二进制以重建这些 bodies。用户同时明确要求不再使用 Actions。因此依据 `AGENTS.md` Protocol 1/2，本任务必须转本地执行。

### 最小数据要求

只允许使用仓库已供应的冻结 development material：

```text
data/development/5m_offset_0.parquet
data/development/5m_offset_1.parquet
data/development/5m_offset_2.parquet
data/development/5m_offset_3.parquet
data/development/5m_offset_4.parquet
data/manifest.json
```

数据边界：

- 标的：`000852.SH` CSI1000 index signal data
- 日期：2015-01-05 至 2020-12-31
- 只用供应的 DataHub-built views
- **禁止本地重新 resample wall-clock frequency**
- 不需要 `1m_official`
- 禁止下载、推断、补造 2021+ 数据
- 禁止用外部市场数据替代缺失文件

请记录最小数据身份：每个 view 的 bar count、最小/最大交易日；条件允许时记录文件 SHA256；记录 manifest validation 状态。大数据始终留在本地。

### 本地执行步骤

#### 1. 安装与边界校验

```bash
python -m pip install -e . editables==0.6
python scripts/validate_theme_package.py
```

记录两个命令的 exit code。

#### 2. 运行 AGENTS.md 最低治理测试 + v0.6.0 identity 单测

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

如果本地资源足够，可以额外跑 full `pytest -q`，但不能用 full pytest 替代下方 decisive calculation。

#### 3. 构建五个 view 的 all-qualified record bodies

如果仓库当前没有现成的 five-view all-qualified runner，可以新增一个**仅执行/导出层**本地脚本。它必须复用 `scripts/run_two_wave_qualified_identity_audit_v060.py` 中完全相同的函数、上游实现和冻结阈值，不能重新设计识别器。

对 `5m_offset_0..4` 每个 view：

- 重建 v0.6.0 qualified candidates；
- 持久化至少以下字段：

```text
record_id
start_time
end_time
five_occurrence_times
form
scale_class
D3
migration_score
margin_pass
range_like
```

用于 decisive identity 的 5-field tuple 必须保持：

```text
(start_time, end_time, five_occurrence_times, form, scale_class)
```

并同时保存 count + digest。

**硬 identity checkpoint：**

生成结果必须首先复现：

```text
qualified:  734 / 717 / 708 / 691 / 688
margin:     727 / 714 / 706 / 689 / 683
range-like:   7 /   3 /   2 /   2 /   5
```

只要任意 view 不匹配：

- 停止 aggregate；
- 输出 `IDENTITY_DRIFT_STOP`；
- 报告实际 count/digest/commit/data identity；
- **不得为了匹配预期改阈值或逻辑。**

#### 4. 执行 frozen all-qualified cross-offset matching

以 `5m_offset_0` 为 main，与 `5m_offset_1..4` 分别比较。

必须严格使用 v0.6.0 protocol 已冻结的两个层级：

**A. broad range-like ownership diagnostic**

main 的 `start_time` 与 `end_time` 均落在 other qualified interval 范围内的 broad ownership 诊断。它只是 denominator / hidden-match diagnostic，不是 decisive identity。

**B. strict geometry identity（decisive）**

候选 match 必须同时满足：

1. `form` 相同；
2. 五个 extremum timestamps 每一个的差都不超过 **±1 个 native 5m bar**；
3. pair span ratio 位于 **[0.8, 1.25]**；
4. 如果存在多个合法 match：归类为 `ambiguous_multiple_match`；**禁止偷偷选择 nearest/best 一个。**

对每个 main qualified record 归类为：

1. `only_main_owned`
2. `broad_range_like`
3. `strict_unique_geometry_match`
4. `ambiguous_multiple_match`

同时输出 `hidden_match_decomposition`，用于解释 broad ownership 中究竟有多少被 strict identity 捕获、多少仍无唯一几何身份、多少被 ambiguity 阻断。

#### 5. 与 v0.5.8 baseline 比较

输出 all-qualified v0.5.8 与 v0.6.0 的同口径 metrics 和 delta：

- only-main-owned fraction
- broad range-like fraction
- strict unique geometry-match fraction
- ambiguous multiple-match fraction
- hidden-match decomposition

必须分别给出 offset1..4 和 aggregate。

如果现有仓库/本地环境**没有 v0.5.8 all-qualified record bodies**，且无法在不改变冻结定义的情况下从同一数据重建，则：

- 如实标记 `INCOMPLETE_BASELINE_COMPARISON`；
- 说明缺失的确切 baseline body/字段；
- **不得把 selected-only v0.5.8 数字冒充 all-qualified baseline。**

如果能通过冻结 v0.5.8 runner 本地重建，允许重建，但必须记录具体 script/function/commit 和同样的数据 identity。

### 建议本地产物

推荐保存在：

```text
cloud_results/local_v060_all_qualified_identity_audit/
```

至少包含：

```text
summary.json
aggregate.json
data_identity.json
run.log
per_view/5m_offset_0.json
per_view/5m_offset_1.json
per_view/5m_offset_2.json
per_view/5m_offset_3.json
per_view/5m_offset_4.json
```

如果新增了仅执行层 helper script，也保存其 patch / commit 信息。

不要上传原始 parquet 或大体积中间数组。云端只需要小型 JSON / Markdown 摘要用于复核。

### 冻结机械路由

只有同时满足：

A. v0.6.0 相对 v0.5.8 的 **all-qualified strict unique geometry-match gain survives**；

B. **only-main-owned fraction materially falls**；

C. unique-match gain **不是主要被 ambiguity 增加所替代**；

才可以返回：

`PASS_TO_D3_MATCHED_SET`

否则返回：

`REJECT_IDENTITY_HYPOTHESIS`

如果因为缺失 v0.5.8 all-qualified baseline bodies无法诚实计算 delta，则返回：

`INCOMPLETE_BASELINE_COMPARISON`

无论哪种结果，总体仍维持 `morphology_replication_not_yet_accepted`，直到独立 morphology labels 验收。

### 本地反馈模板

```markdown
#### 本地反馈 — CL-20260906-002

- status: COMPLETED / FAILED / BLOCKED
- route verdict: PASS_TO_D3_MATCHED_SET / REJECT_IDENTITY_HYPOTHESIS / INCOMPLETE_BASELINE_COMPARISON
- 实际 branch / commit：
- frozen research diff check 命令与 exit code：
- Python / OS：
- 工作区是否干净：

- 数据文件：
- 每 view bar count：
- min/max trading day：
- SHA256（如已记录）：
- manifest validation：

- package validation 命令与 exit code：
- pytest 命令、测试数量与 exit code：
- decisive audit 命令与 exit code：

- v0.6.0 expected qualified count check：
  - offset0:
  - offset1:
  - offset2:
  - offset3:
  - offset4:
- margin / range-like check：
- qualified_records digest（逐 view）：

- per-offset v0.5.8 metrics：
- per-offset v0.6.0 metrics：
- aggregate v0.5.8 metrics：
- aggregate v0.6.0 metrics：
- v0.5.8 → v0.6.0 deltas：

- hidden-match decomposition：
- ambiguity 是否解释了主要 gain：
- only-main-owned 是否 materially falls：
- strict-match gain 是否 survives：

- 本地产物目录：
- summary.json：
- aggregate.json：
- data_identity.json：
- run.log：

- 新增/修改的仅执行层代码：
- 对冻结研究逻辑是否有任何修改：必须说明
- 失败或未验证事项：
```

### 云端收到反馈后的动作

云端收到 `CL-20260906-002` 本地结果后必须：

1. 先标注“本地已反馈”，再独立做可执行范围内的云端复核；
2. 复核 commit/data identity、五视图 expected-count checkpoints、strict matching 与 ambiguity 定义是否完全符合 protocol；
3. 明确区分本地全量执行证据与云端仅对小型结果/代码的复核范围；
4. 将 all-qualified 正式结论写入 v0.6.0 results / `CONTINUE_HERE.md`；
5. 只有 route verdict 经复核为 `PASS_TO_D3_MATCHED_SET`，才允许下一步在 matched set 上重算 D3 label agreement；
6. 若为 `REJECT_IDENTITY_HYPOTHESIS`，停止把 qualified identity repair 当作 D3 稳定性解决路径；
7. 若为 `INCOMPLETE_BASELINE_COMPARISON`，只补缺失 baseline，禁止提前调 D3；
8. PR 保持 Draft，不 merge main；不进入 H1/H2、收益或交易。
