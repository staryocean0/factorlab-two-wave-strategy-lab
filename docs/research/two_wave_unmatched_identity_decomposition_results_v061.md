# v0.6.1 unmatched-identity decomposition：正式结果与云端裁决

日期：2026-09-06

状态：`decomposition_valid_raw_projection_identity_is_primary_next_audit_target`

操作基线：**v0.4.3（不变）**。全局状态仍为 `morphology_replication_not_yet_accepted`。本轮没有修改 recognizer、qualification、direction、packing、outcome 或 trading logic；不授权进入 D1/D2/PAWCT、第三浪、收益、fresh OOS 或生产。

## 1. 冻结问题

结果前协议：`docs/research/two_wave_unmatched_identity_decomposition_protocol_v061.md`。

冻结实现：`bda82c29103080f69f36d7848b40216088895b3a`。

本轮只回答：v0.6.0 Route M 中 offset0 的 canonical qualified identities 在 harmless 5m offset 下大量 unmatched，counterpart 最早在哪个既有 upstream layer 丢失？

Primary attribution 顺序严格保持冻结协议：

1. qualified strict edge non-mutual
2. raw evaluated phase mismatch
3. qualification survival loss
4. evaluated identity non-mutual
5. filtered tuple phase mismatch
6. post-tuple-birth loss
7. tuple identity non-mutual
8. tuple topology/death-certification mismatch
9. birth-scale path shift
10. birth-scale path ambiguous
11. filtered-extremum survival mismatch

五锚 locality 仍是位置对应、每个 timestamp delta `<=5m`；mutual-unique only；不 tie-break；D1/D2/PAWCT/return/outcome 不参与 matching。

## 2. 本轮实际执行方式与证据边界

本轮在 ChatGPT 网页 Chat 的当前 cloud runtime 中实际执行，不使用新的 GitHub Actions，也不是本地模型报告。

### 数据

用户把仓库 `main` ZIP 作为当前 Chat 文件输入。只使用其中已经冻结的：

- `data/development/5m_offset_0.parquet` ... `5m_offset_4.parquet`
- `data/manifest.json`

五份 parquet 的 SHA256 与 frozen manifest 全部一致。没有 resample，没有 2021+，`fresh_oos=false`。

### 代码身份

研究逻辑来自 GitHub frozen commit `bda82c29103080f69f36d7848b40216088895b3a`。

历史正式 artifacts 中已有源码快照的核心文件，先按 Git blob SHA 与 frozen commit 逐个核对，确认一致后才用于当前 runtime，包括 v0.4.3 / v0.5.0 / v0.5.1 / v0.5.2 / v0.5.4 主链。v0.6.0 / v0.6.1 evaluator 从 GitHub frozen commit 读取。

当前 Chat runtime 不是完整 branch checkout，因此该执行**不是**“整仓字节级原样重放”。对当前 runner 用到的 research semantics，使用 frozen source，并以下述硬 controls 作行为身份门槛。

### runtime-only bridges

当前 Chat Python 为 3.13，未安装 `pyarrow`，且 shell 无 GitHub 出站 TCP。为避免把运行环境问题改写成研究缺口，本会话做了两个**不提交仓库、只属于执行层**的 bridge：

1. read-only Parquet bridge：直接解析这批 frozen PyArrow/ZSTD/dictionary flat Parquet，并保持原 manifest SHA / rows / timestamps / OHLC；
2. memory/performance bridge：原 runner 同时常驻五个完整 view 时在约 5.9GB sandbox 中被 OOM killer 终止，exit **137**。随后改成 offset0 常驻、offset1..4 逐个 build → 调用同一 frozen `audit_pair` → save → release 的两视图流式 orchestration。

filtered-extremum survival 的全节点扫描另改成 `(level, kind, timestamp)` 索引 + `±5m` bisect 枚举；该条件与原定义完全相同。使用前做 100 组随机等价检查，原扫描与索引版候选集合 **100/100 PASS**。

这些 bridge 不改变 attribution order、5m tolerance、edge graph、ridge linking、tuple-birth death certification、qualification、D1/D2/PAWCT 或任何 outcome logic。

### 测试与控制

- main governance focused tests：**29/29 PASS**
- v0.6.0 + v0.6.1 helper tests：**17/17 PASS**
- unchanged `validate_theme_package.py`：当前 Chat 因顶层 `import pyarrow.parquet` 不可执行，记录为 runtime dependency failure，不伪装为 PASS
- offset0 独立重建：**38,049 evaluated / 734 qualified / 404 legacy-selected / 38,636 tuple births / 712 canonical**，全部精确复现冻结历史
- streaming formal replay：**exit 0**

因此本报告把证据定义为：**cloud-chat replay with execution-only I/O/orchestration bridges and exact frozen hard-control reproduction**，不称作完整 repo checkout 的字节级独立复验。

## 3. v0.6.0 hard controls 全部精确复现

Qualified counts：

`734 / 691 / 691 / 721 / 746`

Canonical qualified identities：

`712 / 673 / 678 / 700 / 728`

| pair | strict matches | ambiguous main/other | unmatched main/other |
|---|---:|---:|---:|
| offset0 vs 1 | 180 | 1 / 1 | 531 / 492 |
| offset0 vs 2 | 129 | 0 / 0 | 583 / 549 |
| offset0 vs 3 | 129 | 1 / 0 | 582 / 571 |
| offset0 vs 4 | 184 | 1 / 1 | 527 / 543 |

任何一项若漂移，runner 都不得解释 v0.6.1；本次没有漂移。

## 4. Primary attribution：四个 offset 的结果

### offset0 vs offset1，denominator = 531

| attribution | count | fraction |
|---|---:|---:|
| post_tuple_birth_loss | 191 | 35.97% |
| qualification_survival_loss | 108 | 20.34% |
| filtered_extremum_survival_mismatch | 102 | 19.21% |
| tuple_topology_or_death_certification_mismatch | 81 | 15.25% |
| birth_scale_path_shift | 29 | 5.46% |
| birth_scale_path_ambiguous | 17 | 3.20% |
| qualified_strict_edge_nonmutual | 2 | 0.38% |
| tuple_identity_nonmutual | 1 | 0.19% |

### offset0 vs offset2，denominator = 583

| attribution | count | fraction |
|---|---:|---:|
| post_tuple_birth_loss | 195 | 33.45% |
| filtered_extremum_survival_mismatch | 136 | 23.33% |
| qualification_survival_loss | 125 | 21.44% |
| tuple_topology_or_death_certification_mismatch | 100 | 17.15% |
| birth_scale_path_shift | 22 | 3.77% |
| birth_scale_path_ambiguous | 5 | 0.86% |

### offset0 vs offset3，denominator = 582

| attribution | count | fraction |
|---|---:|---:|
| post_tuple_birth_loss | 194 | 33.33% |
| filtered_extremum_survival_mismatch | 139 | 23.88% |
| qualification_survival_loss | 135 | 23.20% |
| tuple_topology_or_death_certification_mismatch | 100 | 17.18% |
| birth_scale_path_shift | 11 | 1.89% |
| birth_scale_path_ambiguous | 2 | 0.34% |
| evaluated_identity_nonmutual | 1 | 0.17% |

### offset0 vs offset4，denominator = 527

| attribution | count | fraction |
|---|---:|---:|
| post_tuple_birth_loss | 209 | 39.66% |
| filtered_extremum_survival_mismatch | 119 | 22.58% |
| qualification_survival_loss | 113 | 21.44% |
| tuple_topology_or_death_certification_mismatch | 74 | 14.04% |
| birth_scale_path_shift | 7 | 1.33% |
| birth_scale_path_ambiguous | 3 | 0.57% |
| qualified_strict_edge_nonmutual | 1 | 0.19% |
| evaluated_identity_nonmutual | 1 | 0.19% |

## 5. 四组 aggregate：问题不是 tie-break，也不是 phase

四个 comparisons 共 **2,223 unmatched pair-observations**：

| attribution | count | fraction |
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

`phase_mismatch_raw_evaluated = 0`；`phase_mismatch_filtered_tuple = 0`。

因此：

- v0.6.0 的大面积 unmatched **不是** mutual-unique evaluator 的 tie 问题；
- 不是 start-phase 翻转主导；
- 也不是简单的 birth-scale level 平移主导（shift + ambiguous 仅约 4.32%）。

## 6. 最大单项 `post_tuple_birth_loss` 的内部机制：raw projection displacement

冻结定义要求：filtered exact-ridge tuple 已经存在 same-phase mutual-unique strict counterpart，但 raw evaluated identity 没有对应 strict counterpart。

789 个该类案例中：

- `raw_projection_displacement_cases = 787`
- `projection_invalid_rows = 2`
- `evaluate_pair_invalid_rows = 0`

即 **787 / 789 = 99.75%** 的 post-tuple loss 不是 projection 无效，也不是 evaluate_pair 报错；而是：

> **同一个已经在 filtered tuple 层稳定匹配的 parent event，投影回 raw-price extrema 后，五个 raw occurrence anchors 的局部 identity 发生了超过一根 5m bar 的位移。**

逐 offset：

- offset1: 191 / 191 displacement
- offset2: 194 / 195 displacement，1 projection invalid
- offset3: 193 / 194 displacement，1 projection invalid
- offset4: 209 / 209 displacement

这使 **filtered tuple → raw-price projection identity** 成为下一轮最优先的独立数学审计对象。

注意：这不是授权放宽 `<=5m` matcher。matcher 是 evaluator；当前证据要求审计 projection 为什么把同一 filtered parent 映成不同 raw anchors，而不是事后扩大 same-event tolerance。

## 7. Qualification survival 仍是独立的大块问题，但不是唯一主因

481 个 `qualification_survival_loss` 中，冻结 rejection reasons 可重叠：

| reason | occurrences |
|---|---:|
| jump_dominated_leg | 262 |
| inefficient_leg | 125 |
| confirmation_too_late | 89 |
| short_leg | 82 |
| short_cycle | 56 |
| amplitude_mismatch | 31 |
| cycle_duration_mismatch | 18 |

因此 qualification 仍需保留为后续独立问题，尤其 `jump_dominated_leg`；但本轮不允许据此调阈值。

## 8. Upstream filtered representation 也仍 materially unstable

`filtered_extremum_survival_mismatch` + `tuple_topology_or_death_certification_mismatch` 合计：

`496 + 355 = 851 / 2223 = 38.28%`

所以不能把所有 instability 都归给 raw projection。即使 projection identity 被修复，上游 filtered extrema / tuple topology 仍可能留下大量 instability。

这也是为什么当前不能把 v0.6.1 解释成“找到一个 bug，修完就回 direction”。

## 9. Session boundary / local-neighborhood overlay

Unmatched observations 的 boundary-tag prevalence：`1618 / 2223 = 72.78%`。

Strict-matched control：`416 / 622 = 66.88%`。

边界附近略有富集，但 strict matched control 本身也有约 2/3 被 boundary tag；因此 session boundary 不是足以解释主体失败的单一原因，只保留为 descriptive overlay。

Local-envelope overlap 中，unmatched identity 的 candidate-count median 为 0 / 0 / 0 / 1；在存在 overlapping candidates 的子集里，minimum positional max-five-anchor displacement 的 median 为：

`96 / 162 / 97 / 96 minutes`

对应 p90 均约 `4,000+ minutes`。因此多数 unmatched 不是“把 5m tolerance 改成 6m/10m 就解决”的边缘 near-miss。

## 10. 正式裁决

v0.6.1 audit acceptance 条件全部满足其 decisive 部分：

1. frozen data / qualified checkpoints reproduced；
2. v0.6.0 pair controls exact reproduced；
3. 每个 main identity 都闭合为 matched / ambiguous / exactly-one primary attribution；
4. attribution 不使用 return/outcome/direction labels；
5. 没有修改 tolerance、qualification threshold、sigma schedule、ridge linking、packing；
6. frozen v0.6.1 code identity 已记录。

执行环境 caveat：unchanged package validator 因当前 Chat 无 `pyarrow` package 不能原样执行；本轮依赖 frozen manifest + runtime Parquet bridge + exact downstream hard controls 校验输入等价。该 caveat 不改写为 PASS。

正式研究结论：

> **v0.6.0 Route M 的 unmatched 不是一个单层问题。最大可定位单项是 filtered exact-ridge tuple 到 raw-price extrema projection 时的 financial-identity displacement；与此同时，filtered-extremum / tuple-topology instability 和 qualification survival 各自仍占 substantial mass。**

因此下一步优先顺序是：

1. **先冻结 raw-projection identity audit/preanalysis**：研究在同一 strict-matched filtered tuple 下，当前 sequential raw-close-extreme projection 为什么产生 >5m raw-anchor identity displacement；
2. 不直接设计 replacement projection；先做只读 attribution / invariance decomposition；
3. 不放宽 cross-view matcher；
4. 不调 qualification；
5. projection 层若能独立稳定后，再重新跑同一 v0.6 identity ladder；
6. upstream filtered-extremum / tuple-topology 作为并列未解决问题，不因 projection 成为最大单项而删除。

**Direction/D1/D2/PAWCT 继续冻结。PR 保持 Draft，不 merge main。**
