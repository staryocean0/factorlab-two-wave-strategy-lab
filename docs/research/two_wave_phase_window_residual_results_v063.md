# v0.6.3 phase-window semantics residual audit：正式结果与云端裁决

日期：2026-09-06

状态：`residual_audit_valid_ordinal0_left_support_is_primary_repair_target`

操作基线仍为 **v0.4.3**。全局状态仍为 `morphology_replication_not_yet_accepted`。本轮没有修改 recognizer、projection、ridge、qualification、direction、packing、outcome 或 trading logic，也不授权进入 D1/D2/PAWCT、第三浪、收益、fresh OOS 或生产。

## 1. 冻结问题与执行身份

结果前协议：`docs/research/two_wave_phase_window_residual_protocol_v063.md`，协议 blob SHA：`85fa0e0712cbabc88116d19e59d8f425377d94fd`。

冻结 evaluator helper blob SHA：`7cda9c4213a7cda7b310d23f97f45d83073908a3`；修正后的 synthetic test blob SHA：`38d856fe9e3b5a9a1b0ab45684d6897482a7f883`。

synthetic gate：**9/9 PASS**。真实执行复用 v0.6.2 已验过的 deterministic per-view cache，仅重新生成 frozen projection windows、canonical-1m residual membership、v0.6.1 post-tuple target membership 与 v0.6.3 attribution；没有把 v0.6.2/v0.6.1 的结果标签作为 attribution truth。

数据仍是仓库冻结五个 native-5m views + `1m_official`，全部 SHA256 / bytes 与 manifest 一致；没有 resampling、没有 2021+、`fresh_oos=false`。

## 2. Hard controls 全部闭合

v0.6.2 canonical-1m residual：

```text
offset1 = 1,578
offset2 = 1,738
offset3 = 1,806
offset4 = 1,718
aggregate = 6,840
```

v0.6.1 post-tuple target residual：

```text
offset1 = 32
offset2 = 28
offset3 = 30
offset4 = 32
aggregate = 122
```

无 control drift，允许解释 v0.6.3。

## 3. Primary attribution：ordinal0 extrapolated left bound 明显主导

四组 6,840 residual pair-observations 的冻结首因分解：

| primary attribution | count | fraction |
|---|---:|---:|
| **ordinal0_extrapolated_left_bound_exclusion** | **4,659** | **68.1140%** |
| sequential_lower_bound_exclusion | 1,403 | 20.5117% |
| filtered_predecessor_upper_bound_exclusion | 465 | 6.7982% |
| mixed_lower_upper_exclusion | 287 | 4.1959% |
| confirmation_tail_upper_bound_exclusion | 26 | 0.3801% |
| mutual_window_overlap_extreme_competition | **0** | **0%** |

逐 offset 的 ordinal0-left 比例：

- offset1: `1187 / 1578 = 75.22%`
- offset2: `1162 / 1738 = 66.86%`
- offset3: `1186 / 1806 = 65.67%`
- offset4: `1124 / 1718 = 65.42%`

因此这不是单一 offset 的偶然现象。

## 4. 最早失配 anchor 也集中在 ordinal0

first canonical-1m displaced ordinal：

```text
ordinal0 = 4,983 / 6,840 = 72.85%
ordinal1 = 374
ordinal2 = 527
ordinal3 = 511
ordinal4 = 445
```

这与 frozen primary attribution 的 ordinal0-left dominance 一致，但二者口径不同：first ordinal 只定位第一个失配位置；primary attribution 还要求对方 canonical extremum 被该窗口的 lower bound 排除且不存在同时 upper exclusion。

## 5. v0.6.1 最关键 target residual 更集中

122 个 v0.6.1 post-tuple residual：

| attribution | count | fraction |
|---|---:|---:|
| **ordinal0_extrapolated_left_bound_exclusion** | **112** | **91.8033%** |
| sequential_lower_bound_exclusion | 7 | 5.7377% |
| filtered_predecessor_upper_bound_exclusion | 2 | 1.6393% |
| confirmation_tail_upper_bound_exclusion | 1 | 0.8197% |

其中 offset1 为 **32/32 ordinal0-left**；offset2 为 27/28；offset3 为 25/30；offset4 为 28/32。

这使 ordinal0 support 不是只在宽泛 universe 上数量大，而是在最初推动 v0.6.1 repair priority 的 target stratum 上更强。

## 6. 不是 window 内 tie / extreme competition

最早失配 ordinal 上 exact canonical-1m extreme tie：

`82 / 6840 = 1.20%`

而 frozen `mutual_window_overlap_extreme_competition` primary category 为 **0**。

也就是说，6,840 个 residual 的 earliest failure 全部至少存在一侧 support-window exclusion；没有出现“双方 selected canonical extrema 都在彼此窗口里，但因为窗口内另一个极值竞争而相差 >5m”的首因案例。

因此当前首要问题不是 `last_argextreme` tie-breaking，也不是需要设计新的窗口内 ranking。

## 7. Session gap 不是主解释

在 earliest displaced ordinal 的 descriptive overlay：

- lunch-gap straddled: `447 / 6840 = 6.54%`
- overnight-gap straddled: `638 / 6840 = 9.33%`
- any session boundary nearby: `1961 / 6840 = 28.67%`

所以交易日午休/隔夜会放大一些 support differences，但不足以解释 68.11% ordinal0-left concentration；该机制在普通连续 session 内也大量存在。

## 8. Sequential propagation 是第二独立问题，但不是本轮首修目标

`sequential_lower_bound_exclusion = 1403 / 6840 = 20.51%`，是第二大类别。

Overlay 中 prior 5m selected time differs 为 `1857 / 6840 = 27.15%`；canonical-1m residual displaced anchors 从 first mismatch 一直形成 suffix 的仅 `615 / 6840 = 8.99%`。

因此 sequential recursion 确实是独立结构问题，但不能把全部 later-anchor disagreement 简化成“第一个错了所以后面都错”。

按照预冻结 interpretation rule，本轮先允许把 ordinal0 support 单独提升为下一 repair target；sequential lower support 保留为后续独立 workstream，不在同一 repair 中顺手修改。

## 9. Window-intersection diagnostic 反证“简单取共同窗口即可解决”

共有 7,972 个 displaced ordinal rows；其中 7,966 个 absolute window intersection 内存在 supplied 1m row，但 intersection projection 只有 **200 / 7966 = 2.51%** 同时位于两侧原 canonical selections 的一根 nominal bar 内。

因此 `intersection(windowA, windowB)` 不能被事后升级为新 runtime projection；它只是诊断。v0.6.3 不支持“直接取两视图共同窗口”这种 cross-view dependent 修复，而且这种规则本身也不能用于单视图 recognizer。

## 10. 对当前 ordinal0 公式的语义裁决

现行第一个 raw phase support 下界：

```text
left = max(0, 2*f0 - f1)
```

是在**当前 view 的 bar-index 坐标**上向左镜像 `f0 -> f1` 的 bar count，然后把该 index 映回 absolute time。

v0.6.2 已证明 filtered parent 在大量 cases 上是同一 canonical event；v0.6.3 又证明 canonical 1m path 下最早 residual 主要来自这个 left support 把另一 slicing 下的 canonical first extremum 排除。

因此正式裁决是：

> **bar-index extrapolated ordinal0 support is not a sufficiently cross-slicing-invariant financial support definition for the current parent projection.**

这不是说任何“绝对时间镜像公式”已经被验证正确，也不是授权使用 1m 路径作为生产输入。它只确定了下一 repair experiment 应优先解决的数学对象：**ordinal0 left-support invariant**。

## 11. 下一步允许范围

下一步必须另开 v0.6.4 repair preanalysis/protocol，并只研究 ordinal0 support。至少要预先规定：

- support 必须是单视图可计算、prefix causal；
- 不得依赖其他 offset 的窗口或匹配结果；
- 不得用 D1/D2/PAWCT、收益、outcome 选择规则；
- 不得改变 ordinal1..4 的现行 upper/lower semantics；
- synthetic cases 必须覆盖 regular session、lunch gap、overnight gap、one-bar slicing shift、left-censoring；
- 任何候选规则在看金融 replay 前必须冻结；
- canonical-1m 只允许做审计/评估，不自动成为 runtime 数据依赖。

v0.6.4 若提出多个候选，必须事前冻结比较口径，不能看结果再拼规则。

## 12. 当前状态

`morphology_replication_not_yet_accepted`

操作基线仍为 `v0.4.3`。Exclusive packing 仍 downstream；Direction/D1/D2/PAWCT、H1/H2、第三浪、收益、fresh OOS、paper trading、production 全部继续冻结。
