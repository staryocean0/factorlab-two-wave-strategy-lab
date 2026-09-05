# v0.5.3 单组件协议：在 exact-ridge hierarchy 下移除 legacy raw ER gate

日期：2026-09-06

状态：`results_before_code_frozen`

操作基线：**v0.4.3（不变）**。

研究候选链：v0.5.2 exact-ridge hierarchy 已通过 `parent_identity_pass_qualification_pending`；随后只读 qualification attribution、D0–D4 ER 定义竞争和 legacy-ER redundancy POC 已完成。v0.5.3 只验证一个已经事前确定的组件变化：

> **保留 v0.5.2 candidate identity / raw projection / information time / 其它 qualification / D1 / ledger 不变，仅不再把 raw-close `inefficient_leg` 作为 parent-scale qualification rejection gate。**

本轮仍不研究收益、第三浪、交易或生产。

## 1. 数学动机

v0.4.x 没有真正层级 parent representation，raw ER

`|x_b-x_a| / sum|Δx| >= 0.5`

承担的是“raw pivot-to-pivot leg 内部不应过度曲折”的代理职责。

v0.5.2 已通过 time-causal scale-space extremum ridges、child-ridge death 和 exact parent tuple 明确编码父级结构。后续证据：

1. 五 offset parent-like single failure 中 `inefficient_leg` 为稳定第一瓶颈；
2. birth/prebirth ridge-level ER 近乎饱和，说明同尺度 straightness 与 parent-extrema representation 高度重复；
3. filtered raw-interval ER 出现 11–21% raw-direction disagreement；
4. 只删除 raw ER 的 POC 显著富集 absorbed-micro parent structures，同时四项 native offset IoU 全部改善，安全反例不退化。

因此本轮不是“降低 0.5”，而是检验该门在新 representation 下是否应该退出 parent-scale qualification architecture。

## 2. 唯一代码变化

建立独立 v0.5.3 wrapper/component：

1. 先调用**原封不动**的 v0.5.2 `build_ridge_run`；
2. 对 `evaluated_records` 深拷贝；
3. 从 `scale_rejection_reasons` 中仅移除 `inefficient_leg`；
4. 其余 reasons 原样、原顺序保留；
5. `scale_qualified = (remaining_reasons == [])`；
6. qualified record 的 `classification` 使用 v0.5.2 已冻结 `geometric_direction_diagnostic`；未 qualified 为 `not_same_scale`；
7. 用原 `CharacteristicExclusiveLedger` 完整重放 publication；
8. raw `leg_paths[*].efficiency` 保留为 audit 字段，不删除、不重算。

不允许改：

- ridge nodes / edges / deaths / anomaly policy；
- tuple birth / birth scale / raw projection；
- `min_leg_efficiency=0.5` 的计算代码本身（仅不作为 parent rejection gate）；
- short/long leg、cycle、pair、duration ratio、amplitude、jump、flat、day、wall、confirmation 任何门；
- D1 direction geometry；
- ledger priority/non-overlap；
- data、sigma lattice 或任何 case-specific 参数。

## 3. 工程与隔离硬门

### 3.1 unit tests

必须覆盖：

- 仅有 `inefficient_leg` → v0.5.3 qualified；
- `inefficient_leg + jump` → 只剩 jump，仍 rejected；
- 原 qualified → 完全保留；
- classification 只因 qualification 状态恢复到 frozen geometric diagnostic；
- identity fields 不变；
- raw ER audit 数值不变；
- ledger 仍 deterministic/non-overlap。

### 3.2 full-sample identity equivalence

对六视图：

- v0.5.3 与 v0.5.2 的 ridge nodes / edges / deaths / anomalies / tuple births / raw projection 必须逐字段相同；
- evaluated record identity、raw five points、birth scale、confirmation、known_at 必须相同；
- 除 `inefficient_leg` 外 rejection reasons 必须相同；
- newly-qualified 集合必须精确等于 v0.5.2 `reasons == ['inefficient_leg']`。

任一失败 = 工程失败。

## 4. 真实因果门：18 次 prefix replay

必须对：

- `5m_offset_0..4`
- `1m_official`

分别在 25% / 50% / 75% 独立从头重建，共 **18 次**。

在 cutoff 前比较：

- v0.5.2 ridge lineage / birth / projection；
- v0.5.3 evaluated records；
- v0.5.3 selected records；
- qualification reasons / classification / selected / suppressed-by。

`confirmed_rewrite_count` 必须全部为 0。

## 5. 五 native 5m 正式回归指纹

前置 POC 已在相同冻结数据上给出确定性指纹；正式实现若数学逻辑完全相同，应精确复现：

| view | qualified | selected |
|---|---:|---:|
| o0 | **780** | **431** |
| o1 | **714** | **396** |
| o2 | **700** | **387** |
| o3 | **737** | **394** |
| o4 | **764** | **411** |

这不是结果选择标准，而是单组件实现的 regression fingerprint；不匹配必须先解释工程差异，不能调参追回。

## 6. morphology / stability hard audit

### 6.1 parent-like absorption

继续报告 existing/new/final qualified & selected 的 `v043_excess_local_pivots_beyond_five`。

正式结果至少必须复现 POC 的方向：newly-qualified / newly-selected 在五个 offset 上均比原 v0.5.2 显著富集 parent-like objects。不得把数量增加本身称为成功。

### 6.2 native offset IoU

在现有 1m timestamp grid 上比较 `(start,end]` ownership。

POC 指纹：

- o1 ≈ 43.33%
- o2 ≈ 37.43%
- o3 ≈ 40.04%
- o4 ≈ 44.97%

正式实现应确定性复现。若不匹配，先视为实现/数据问题。

IoU 仍只代表边界稳定性，不代表准确率。

### 6.3 safety cases

- case_00 exact parent `[48720,48749,48754,48768,48801]` 必须继续 rejected，remaining reasons = `corresponding_leg_duration_mismatch + jump_dominated_leg`；
- case_02 仍 0 qualified / 0 selected；
- case_11/14 不得出现跨数周巨型 publication；
- 2018/2019/2020 固定窗口完整披露；不得用于调参。

## 7. 正式判定分支

### `v053_single_component_confirmed_qualification_architecture_still_pending`

若：

- isolation 全过；
- 18 prefix 全过；
- POC deterministic fingerprints 复现；
- safety audits 不退化；

则确认：在 v0.5.2 exact-ridge hierarchy 下，legacy raw ER 不再作为 parent qualification gate。

这只完成 qualification architecture 的**一个组件确认**，不意味着整体 morphology 已验收，也不自动升级操作基线。

### `v053_confirmation_failed`

若 formal implementation 无法复现 POC 或出现 causal rewrite / safety regression，则不采用 removal，回到 v0.5.2 parent-identity safe stop。

## 8. 通过后的下一步

若 v0.5.3 确认通过，**不得机械继续放松 duration/jump**。必须先对 v0.5.3 固定 records 重新做 qualification failure attribution，确认新的独立瓶颈，再做数学预分析。

收益、H1/H2、第三浪和交易继续禁止。
