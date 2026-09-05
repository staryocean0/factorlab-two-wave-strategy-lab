# v0.5.3 前置单门消融：legacy raw-ER redundancy protocol

日期：2026-09-06

状态：`results_before_code_frozen_read_only_ablation`

本轮仍不是完整 v0.5.3 recognizer 晋级。目的仅是回答一个已经由 v0.5.2 hierarchy + qualification attribution + D0–D4 definition competition 共同提出的问题：

> 在 exact-ridge hierarchy 已经定义 parent extrema / parent legs 后，v0.4.x 遗留的逐 bar raw-close `inefficient_leg` 是否仍提供独立形态信息，还是已经成为与父级 representation 冲突的重复约束？

操作基线继续是 **v0.4.3**；v0.5.2 仍只保留为 parent-identity representation。

## 1. 结果前唯一组件变化

对 v0.5.2 `build_ridge_run` 生成的 **同一 evaluated records** 做后置反事实副本：

1. 保留 record identity、ridge IDs、tuple birth、raw five points、birth scale、information time、全部 raw diagnostics；
2. 只从 `scale_rejection_reasons` 中删除字符串 `inefficient_leg`；
3. 其它所有 rejection reasons 原样、原顺序保留；
4. `scale_qualified := (remaining_reasons == [])`；
5. 若新 qualified，则 `classification := geometric_direction_diagnostic`；否则保持 `not_same_scale`；
6. 用**同一个** `CharacteristicExclusiveLedger` priority / greedy non-overlap 规则重建 publication。

不得：

- 改 `min_leg_efficiency=0.5` 后声称是阈值优化；本轮是“门存在/不存在”的职责消融；
- 改 raw ER 数值本身；必须继续输出作审计；
- 改 jump/flat/duration/amplitude/cycle/pair/confirmation/day/wall-span 任一门；
- 改 D1；
- 改 ridge linking、tuple birth、raw projection；
- 用 case、IoU、selected count、收益反调其它参数。

## 2. 为什么这个消融在数学上合法

v0.4 的 raw ER 原本承担“一个 raw pivot-to-pivot leg 不应内部过度曲折”的代理职责，因为当时没有真正父级 hierarchy。

v0.5.2 已使用 time-causal scale-space extremum ridges，并由 child-ridge death 形成 exact parent tuple。随后 D0–D4 定义竞争证明：

- 在 birth / prebirth ridge extrema 之间重新计算 same-scale ER 会趋近 1，判别力消失；
- 在 raw projected 时间端点上计算 filtered ER 又产生 11–21% raw direction disagreement；
- 没有一个“平滑 ER 替换公式”通过预先冻结的语义门。

因此必须直接测试：raw ER 是否只是旧 representation 的补丁，而不是新 hierarchy 下仍必要的独立门。

## 3. 五个 native 5m 的结果前审计

先只跑 `5m_offset_0..4` full samples；不跑收益，不跑 1m，不进入交易。

每个 view 输出：

- evaluated / qualified / selected before vs no-ER；
- newly qualified = 原 reasons **仅**为 `inefficient_leg` 的对象；
- newly selected；
- newly qualified / selected 中吸收额外 v0.4.3 micro pivots 的数量与比例；
- selected excess micro-pivot quantiles；
- birth-scale distribution；
- labels；
- 每个其它 rejection reason 的计数差必须严格为 0。

## 4. 结构性晋级门——“更多”不是成功

本轮只允许以下判定。

### A. identity / isolation hard gate

必须全部成立：

- v0.5.2 evaluated record IDs、ridge IDs、five points、birth scale、confirmation 等 identity fields 逐条完全相同；
- 除 `inefficient_leg` 外所有 rejection reason 逐条完全相同；
- 原 qualified records 全部继续 qualified；
- no-ER newly qualified 必须精确等于原来 `reasons == ['inefficient_leg']` 的对象。

任一失败 = 工程失败，不解释为研究结果。

### B. parent-like enrichment gate

新增对象是否具有 hierarchy 语义，用 `v043_excess_local_pivots_beyond_five > 0` 作**事前固定代理**，不是准确率标签。

必须报告：

- existing qualified parent-like fraction；
- newly-qualified parent-like fraction；
- final qualified parent-like fraction；
- same for selected。

希望看到 newly-qualified 明显富集 parent-like 结构；若新增主要是 `excess=0` 的局部对象，倾向否定 ER removal。

不设置结果后百分比阈值，不允许以候选数量增长作晋级依据。

### C. native offset stability gate

在统一 1m 时间轴上按同一 `(start,end]` 所有权定义比较 offset_0 vs offset_1..4 IoU。

- 与冻结 v0.5.2 比较；
- 若四项 IoU **全部下降**，直接否定；
- 若均值明显下降且没有 parent-like 结构补偿，也否定；
- 只允许把 IoU 当边界稳定性，不当准确率。

### D. fixed safety cases

- **case_00**：目标 `[48720,48749,48754,48768,48801]` 删除 efficiency 后仍必须因 `corresponding_leg_duration_mismatch + jump_dominated_leg` 被拒绝；若变 qualified，说明隔离实现错误。
- **case_02**：旧 90/3 假浪不得复活为 selected；
- **case_11 / case_14**：不得产生跨数周巨型 published five-point；
- 2018-06-20 / 2019-04-15 / 2020-07-15 只记录，不以“变好看”决定实验。

### E. morphology breadth guard

对新 selected 的：

- pair duration；
- leg durations；
- birth scale；
- absorbed micro pivots；
- raw ER distribution

全部披露。若 ER removal 主要把极低 raw-ER、局部低层级对象大量塞进 ledger，而 parent-like 吸收没有同步改善，否定。

## 5. 本轮不做的事情

- 不做 D1 改造；
- 不研究 duration ratio；
- 不研究 jump threshold；
- 不调整 0.5；
- 不做收益或交易；
- 不把人工固定案例当训练标签；
- 不把 POC 直接升级为操作基线。

## 6. 判定分支

### `legacy_raw_er_redundant_candidate`

只有 identity/isolation 全过，parent-like enrichment 明确，offset 不系统性恶化，安全反例不退化，才允许下一步把“删除 legacy raw ER”写成真正 v0.5.3 结果前协议并补 18 次 prefix。

### `legacy_raw_er_still_needed`

如果删除后主要释放局部噪声、offset 全面恶化或安全案例退化，则 raw ER 仍承担独立职责；不进入 v0.5.3 removal。

### `qualification_architecture_unresolved`

如果两边信号混合，则停止单门试错，转向 qualification architecture（例如 persistence/significance）预研究，不继续堆阈值。
