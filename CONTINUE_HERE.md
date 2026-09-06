# 两浪研究继续入口：v0.6.1 unmatched-identity decomposition 已冻结，CL-003 待真实五视图 replay（2026-09-06）

## 当前安全状态

冻结上游仍是：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

v0.6.0 已正式裁决 **Route M**；操作基线仍为 **v0.4.3**。全局状态仍为：

`morphology_replication_not_yet_accepted`

PR #1 保持 Draft，不合并 main。禁止进入 H1/H2、第三浪、收益/P&L、fresh OOS、paper trading 或 production；`trade_authority=false`。

## 当前研究链

**v0.5.0 TCSS representation ✅ → v0.5.1 sliding family ❌ → v0.5.2 exact-ridge identity ✅ → v0.5.4 full-cycle qualification ✅ → v0.5.5 D1 attribution → v0.5.6 D2 multiview ❌ → v0.5.7b endpoint-D2 ❌ → v0.5.8 PAWCT selected-output R1 ❌ → v0.5.9 event-identity confound attribution → v0.6.0 financial identity / exclusive packing 解耦 → five-view replay = Route M → v0.6.1 unmatched-identity decomposition 已预分析、冻结并实现，等待 CL-003 真实五视图 replay。**

## v0.6.0 已闭合

正式结果：`docs/research/two_wave_qualified_identity_results_v060.md`。

硬证据：

- raw qualified counts：`734 / 691 / 691 / 721 / 746`
- canonical qualified identities：`712 / 673 / 678 / 700 / 728`
- identity prefix：**15/15 PASS**，confirmed rewrite count `0`
- all-qualified strict matches offset0 vs 1..4：`180 / 129 / 129 / 184`
- main unmatched：`531 / 583 / 582 / 527`，约 74%–82%
- ambiguity 极低：`1/1, 0/0, 1/0, 1/1`
- strict qualified matches 被 legacy packing 隐藏：`60.56% / 58.14% / 57.36% / 56.52%`

因此正式判定是 **Route M**：exclusive packing 是重大污染源并永久保持 downstream，但 qualified financial identity 自身在 harmless native-5m slicing 上仍 materially unstable。Direction/PAWCT 权限继续冻结。

## v0.6.1 当前研究问题

不修模型，先回答：

> 对 offset0 中没有进入 v0.6.0 mutual-unique strict same-event match 的 canonical qualified identities，最早在哪个既有 upstream layer 丢失 harmless-offset counterpart？

v0.6.1 是 attribution audit，不是 repair POC。

预分析：`docs/research/two_wave_unmatched_identity_decomposition_preanalysis_v061.md`  
冻结协议：`docs/research/two_wave_unmatched_identity_decomposition_protocol_v061.md`

## v0.6.1 冻结 attribution order

每个 v0.6.0 unmatched main identity 按下列顺序归因，**第一个满足项就是 primary attribution**：

1. `qualified_strict_edge_nonmutual`
2. `phase_mismatch_raw_evaluated`
3. `qualification_survival_loss`
4. `evaluated_identity_nonmutual`
5. `phase_mismatch_filtered_tuple`
6. `post_tuple_birth_loss`
7. `tuple_identity_nonmutual`
8. `tuple_topology_or_death_certification_mismatch`
9. `birth_scale_path_shift`
10. `birth_scale_path_ambiguous`
11. `filtered_extremum_survival_mismatch`

所有五锚比较仍冻结为 ordered position-wise、每个 absolute timestamp delta `<=5 minutes`。mutual-unique only，不 tie-break。phase-ignored relation 只允许诊断 phase mismatch。

canonical identity 的 upstream representative 只能使用 causal `first_record_id`；不得挑最容易跨 view 匹配的 member。

## v0.6.1 已完成实现

冻结实现 commit：

`bda82c29103080f69f36d7848b40216088895b3a`

新增：

- `src/factor_lab/visual_structure/two_wave/unmatched_identity_decomposition_v061.py`
- `scripts/run_two_wave_unmatched_identity_decomposition_v061.py`
- `tests/unit/test_two_wave_unmatched_identity_decomposition_v061.py`

没有修改 v0.5.2 ridge linking、v0.5.4 qualification、v0.6.0 matcher、packing、D1/D2/PAWCT 或任何 outcome/trading 逻辑。

由于 v0.5.2 每个 native-5m view 约有 36k–38k evaluated records / tuple births，朴素全笛卡尔 strict-edge graph 不可接受。实现使用第一锚点 `±5m` 索引窗口加速；这是合法 strict edge 的必要条件，因此边集合与原定义完全等价，不是新 matcher。

云端已完成：

- 新增 Python 文件 `py_compile`：PASS
- isolated helper unit tests：**9/9 PASS**
- indexed graph vs brute-force exact edge definition：50 random seeds × phase-aware/phase-ignored = **100/100 PASS**
- deterministic test 固化 indexed graph 与 brute-force edge graph 等价

这些不是正式五视图 replay 的替代。

## 当前真实执行阻断

最新 `AGENTS.md` 已明确：repo 中 parquet 本身不缺失，不能再把“二进制无法文本预览”当作缺数据。

云端已按该规则真实尝试执行：

1. GitHub blob 直取 `5m_offset_0.parquet`：connector 报 `UnicodeDecodeError`，无法把二进制送入当前 Python runtime；
2. 当前 container 直接 `git clone` public repo：exit `128`，`Could not resolve host: github.com`。

因此阻断是当前 runtime 的 **DNS/network + binary connector transport**，不是源数据缺失。已满足 `AGENTS.md` 允许本地 handoff 的“真实执行失败并记录错误”条件。

对应交接：`docs/ops/cloud_local_communication.md` → **CL-20260906-003**。

## CL-003 本地唯一任务

本地模型只执行冻结实现的真实 repo tests + five-view replay，不重新设计实验。

执行前必须证明 frozen implementation commit 之后研究文件无漂移：

```bash
git checkout codex/two-wave-phase1-20260905
git pull --ff-only

git diff --exit-code \
  bda82c29103080f69f36d7848b40216088895b3a..HEAD -- \
  src tests scripts docs/research data pyproject.toml
```

最后一条必须 exit 0。

随后按 CL-003 跑 focused pytest 与：

```bash
python scripts/run_two_wave_unmatched_identity_decomposition_v061.py \
  --output cloud_results/local_v061_unmatched_identity_decomposition \
  | tee cloud_results/local_v061_unmatched_identity_decomposition/run.log
```

runner 内置 v0.6.0 hard control assertions：

```text
qualified: 734 / 691 / 691 / 721 / 746
main canonical: 712
offset1: matches 180, ambiguity 1/1, unmatched 531/492
offset2: matches 129, ambiguity 0/0, unmatched 583/549
offset3: matches 129, ambiguity 1/0, unmatched 582/571
offset4: matches 184, ambiguity 1/1, unmatched 527/543
```

任何 control drift 都不得继续解释 decomposition。

## v0.6.1 formal outputs

应生成：

```text
cloud_results/local_v061_unmatched_identity_decomposition/summary.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_1.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_2.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_3.json
cloud_results/local_v061_unmatched_identity_decomposition/details_offset_4.json
cloud_results/local_v061_unmatched_identity_decomposition/data_identity.json
cloud_results/local_v061_unmatched_identity_decomposition/run.log
```

结果必须满足每个 offset：

`strict matched + v0.6.0 ambiguous + exactly-one primary attribution = 712 main canonical identities`

本地不得根据 decomposition 数字直接改模型。云端收到 CL-003 反馈后才做正式 attribution adjudication；任何 repair 都必须另开新的 preanalysis/frozen protocol。

## 允许的 diagnostics / 禁止的解释

允许：

- qualification rejection-reason frequency；
- tuple projection/evaluate diagnostics；
- same-level / any-level filtered-extremum survival；
- session-boundary prevalence overlay；
- local-envelope candidate count 与 minimum max-anchor displacement overlay。

禁止：

- 看完 near-miss distribution 后扩大 5-minute tolerance；
- 根据 rejection reasons 调 v0.5.4 thresholds；
- 根据 decomposition 重新链接 ridge；
- 按哪个分类“结果最好”选择 causal member；
- 回到 D1/D2/PAWCT；
- 使用收益、outcome、P&L；
- 进入 H1/H2 / third-wave / trading；
- 使用 GitHub Actions。

## 优先阅读

1. `docs/ops/cloud_local_communication.md` — CL-003
2. `docs/research/two_wave_unmatched_identity_decomposition_protocol_v061.md`
3. `docs/research/two_wave_unmatched_identity_decomposition_preanalysis_v061.md`
4. `scripts/run_two_wave_unmatched_identity_decomposition_v061.py`
5. `src/factor_lab/visual_structure/two_wave/unmatched_identity_decomposition_v061.py`
6. `tests/unit/test_two_wave_unmatched_identity_decomposition_v061.py`
7. `docs/research/two_wave_qualified_identity_results_v060.md`
8. `cloud_results/local_v060_qualified_identity_audit/summary.json`

**当前唯一允许推进的 formal empirical step 是 CL-003。**