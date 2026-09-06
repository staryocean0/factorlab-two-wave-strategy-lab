# 两浪研究继续入口：v0.6.1 decomposition 已闭合，下一步先审计 raw-projection identity（2026-09-06）

## 当前安全状态

冻结上游仍是：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

v0.6.0 正式裁决仍为 **Route M**。操作基线仍为 **v0.4.3**；全局状态仍是：

`morphology_replication_not_yet_accepted`

PR #1 保持 Draft，不合并 main。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 当前研究链

**v0.5.0 TCSS representation ✅ → v0.5.1 sliding family ❌ → v0.5.2 exact-ridge identity ✅ → v0.5.4 full-cycle qualification ✅ → v0.5.5–v0.5.8 direction routes未通过 → v0.5.9 identity confound attribution → v0.6.0 financial identity / exclusive packing 解耦 = Route M → v0.6.1 unmatched-identity decomposition ✅ → 下一优先研究对象：filtered tuple → raw-price projection identity。**

## v0.6.1 已正式闭合

结果前协议：

- `docs/research/two_wave_unmatched_identity_decomposition_preanalysis_v061.md`
- `docs/research/two_wave_unmatched_identity_decomposition_protocol_v061.md`

冻结实现：

`bda82c29103080f69f36d7848b40216088895b3a`

正式结果：

`docs/research/two_wave_unmatched_identity_decomposition_results_v061.md`

可审计小产物：

- `cloud_results/cloud_chat_v061_unmatched_identity_decomposition/summary.json`
- `cloud_results/cloud_chat_v061_unmatched_identity_decomposition/data_identity.json`
- `cloud_results/cloud_chat_v061_unmatched_identity_decomposition/execution_receipt.json`

### 执行边界

本轮最终由 ChatGPT 网页 Chat 当前 cloud runtime 实际完成。数据使用用户上传到当前 Chat 的仓库 main ZIP 中冻结 parquet；研究代码来自 GitHub frozen commit。

这不是完整 branch checkout 的字节级原样重放。当前 Chat 缺 `pyarrow` 且约 5.9GB RAM，因此使用了只属于 runtime 的 read-only Parquet bridge、两视图流式 orchestration 和等价的 filtered-extremum time index。它们均不提交 research source。

证据门槛：

- main governance focused tests：29/29 PASS
- v0.6.0 + v0.6.1 helper tests：17/17 PASS
- indexed survival vs original scan：100/100 random equivalence PASS
- unchanged `validate_theme_package.py` 因当前 runtime 顶层缺 `pyarrow` package 未原样通过，保留 caveat，不伪装为 PASS
- 原五视图同时常驻 runner：OOM exit 137
- 两视图流式、同 frozen attribution/matcher 逻辑 replay：exit 0

最重要的是所有 frozen behavioral controls 精确复现。

## v0.6.0 controls 精确复现

Qualified：

`734 / 691 / 691 / 721 / 746`

Canonical：

`712 / 673 / 678 / 700 / 728`

| pair | strict matches | ambiguous main/other | unmatched main/other |
|---|---:|---:|---:|
| offset0 vs 1 | 180 | 1 / 1 | 531 / 492 |
| offset0 vs 2 | 129 | 0 / 0 | 583 / 549 |
| offset0 vs 3 | 129 | 1 / 0 | 582 / 571 |
| offset0 vs 4 | 184 | 1 / 1 | 527 / 543 |

Offset0 独立重建也精确得到：

`38,049 evaluated / 734 qualified / 404 legacy selected / 38,636 tuple births / 712 canonical`。

## v0.6.1 primary attribution

四组比较合计 **2,223 unmatched pair-observations**：

| primary attribution | count | fraction |
|---|---:|---:|
| **post_tuple_birth_loss** | **789** | **35.49%** |
| filtered_extremum_survival_mismatch | 496 | 22.31% |
| qualification_survival_loss | 481 | 21.64% |
| tuple_topology_or_death_certification_mismatch | 355 | 15.97% |
| birth_scale_path_shift | 69 | 3.10% |
| birth_scale_path_ambiguous | 27 | 1.21% |
| qualified_strict_edge_nonmutual | 3 | 0.13% |
| evaluated_identity_nonmutual | 2 | 0.09% |
| tuple_identity_nonmutual | 1 | 0.04% |

Raw-evaluated 与 filtered-tuple 两层的 phase mismatch 均为 **0**。

因此大面积 unmatched 不是 tie-break、不是 phase flip，也不是简单 birth-scale shift 主导。

## 最大单项：post-tuple loss 几乎全部是 raw projection displacement

`post_tuple_birth_loss` 的冻结语义是：

> other view 中已经存在 same-phase、mutual-unique、五个 filtered anchors 全部 `<=5m` 的 exact-ridge tuple counterpart，但到 raw evaluated identity 层就失去了 strict counterpart。

789 个案例中：

- raw projection displacement：**787**
- projection invalid：2
- evaluate_pair invalid：0

即 **99.75%** 的 post-tuple loss 是 filtered tuple 稳定存在、projection 也有效，但 sequential raw-price projection 把对应金融事件映射到相差超过一根 5m bar 的 raw anchors。

所以目前最优先的下一层不是放宽 matcher，而是审计：

> **为什么同一个已经跨 slicing 稳定匹配的 filtered parent tuple，会被当前 raw projection 映射成不同的 raw financial identity？**

## 其他未解决层不能删除

即使 projection 是最大单项，仍有：

- filtered-extremum survival mismatch：22.31%
- tuple topology/death certification mismatch：15.97%
- qualification survival loss：21.64%

前两者合计 **38.28%**，说明 upstream filtered representation 自身仍 materially unstable。

Qualification-survival 的 rejection reasons 中 `jump_dominated_leg` 最多，但 v0.6.1 不授权调 threshold。

Session boundary unmatched prevalence 72.78%，strict-matched control 66.88%；只略有富集，不足以作为主体解释。Local-envelope overlapping candidate 子集的 minimum max-five-anchor displacement median 为 96/162/97/96 分钟，也不支持把 5m matcher 事后扩大一点作为解决办法。

## 下一步允许做什么

下一步先做新的 **raw-projection identity preanalysis/audit**，而不是直接替换 projection formula。

新的结果前工作至少要回答：

1. 当前 `sequential_raw_close_extreme_inside_filtered_phase_bounds` 对同一 strict-matched filtered tuple，raw anchor displacement 分别发生在哪几个 anchor position；
2. displacement 是否来自 phase-bound interval 边界移动、同 interval 多个 raw extrema 的选择不唯一、极值 plateaus/ties、或 filtered endpoint 的小变化导致 raw argmax/argmin 跳转；
3. 当前 raw projection 在单视图 prefix 下虽然 causal，是否还缺少跨 slicing 的 financial-identity invariance；
4. 在不看 D1/收益/outcome 的情况下，什么数学性质才应约束一个合法 parent→raw projection；
5. 在任何 replacement projection 提案出现前，先冻结 diagnostic relation 与 synthetic counterexamples。

仍然禁止：

- 事后放宽 5m matcher；
- 调 v0.5.2 ridge linking / tuple birth 来救 projection；
- 调 v0.5.4 qualification thresholds；
- 根据 D1/D2/PAWCT 或收益选 projection；
- 回到 direction 或第三浪；
- 使用新的 GitHub Actions。

## 优先阅读

1. `docs/research/two_wave_unmatched_identity_decomposition_results_v061.md`
2. `cloud_results/cloud_chat_v061_unmatched_identity_decomposition/summary.json`
3. `cloud_results/cloud_chat_v061_unmatched_identity_decomposition/execution_receipt.json`
4. `docs/research/two_wave_unmatched_identity_decomposition_protocol_v061.md`
5. `src/factor_lab/visual_structure/two_wave/extremum_ridge_v052.py`
6. `src/factor_lab/visual_structure/two_wave/characteristic_scale_v051.py` 中 frozen raw projection

**当前下一 formal research step：先冻结 raw-projection identity audit；不得直接修公式。**
