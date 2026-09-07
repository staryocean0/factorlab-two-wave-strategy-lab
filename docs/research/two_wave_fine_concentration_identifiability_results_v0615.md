# v0.6.15 fine-concentration identifiability under native 5m OHLC：正式结果与云端裁决

日期：2026-09-07

状态：`structural_bounds_fail_data_consistency_or_oracle_coverage`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮没有修改 qualification、threshold、identity、matcher、projection、publication、roughness candidate、direction、outcome 或 trading logic。

## 1. 结果前冻结与 synthetic gates

- preanalysis blob `35a327213c349e779090b44f72e0d64c7be43e02`
- protocol blob `231622c2e694f1283f60e74ab38c088b031a7e4c`
- helper blob `03a534f072e7cd11753e7bbf54dc6333995cb9cb`
- test blob `53ce8c4d6b3612e6655410b3ffd43cba2853b3a9`
- synthetic tests **8/8 PASS**

数学 outer-bound helper 本身通过了 vertex TV maximum、feasible hidden paths coverage、profile bounds、scale invariance 与 no-oracle API 等 gates。

## 2. Hard controls

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
fine profile defined = 737,070
oracle-comparable strict pair-legs = 117,805
```

无 upstream behavioral drift。

## 3. Frozen hidden-path information-set assumption 在 offset session boundaries 上失败

v0.6.15 冻结模型假设每个相邻 native close transition 都对应恰好五个 supplied-1m close increments，并且这些 hidden minute closes 全部受当前 native bar `[low,high]` 包络。

真实 offset views 中，offset1–4 几乎每天午休和隔夜边界都会出现 `fine index difference = 10`：offset slicer 为保持固定 origin 会丢弃 session 边界 partial bars，因此两个相邻 native closes 之间包含一段不属于“当前完整 5m bar”的交易分钟。

Used-transition gate：

```text
offset0: used 70,096; non-five/missing 7;    exact-five envelope violations 9
offset1: used 67,182; non-five/missing 2,927; exact-five envelope violations 10
offset2: used 67,165; non-five/missing 2,926; exact-five envelope violations 6
offset3: used 67,167; non-five/missing 2,928; exact-five envelope violations 6
offset4: used 67,184; non-five/missing 2,927; exact-five envelope violations 8
```

所以这不是零星数据坏点，而是 slicer/session semantics 与冻结 hidden-path model 不一致。

## 4. 影响是 material，不允许继续解释 tightness

Published legs 至少包含一个违反该 model 的 transition：

```text
offset0    335 / 152,704 = 0.22%
offset1 50,729 / 146,948 = 34.52%
offset2 50,761 / 146,476 = 34.65%
offset3 50,691 / 145,920 = 34.74%
offset4 50,630 / 145,056 = 34.90%
```

更重要的是，在冻结的 **117,805** oracle-comparable strict pair-leg universe 中：

```text
35,905 / 117,805 = 30.48%
```

至少一侧不满足 frozen five-hidden-step/current-bar-envelope model。

Frozen protocol 明确规定任何 material data-clock/bound assumption violation 都必须先停止 tightness interpretation。因此本轮没有根据 remaining subset 讨论 bounds 宽窄，也没有删掉 session-boundary legs 后继续“通过”。

## 5. 正式裁决

> **`structural_bounds_fail_data_consistency_or_oracle_coverage`**

这里的失败首先是 **data-consistency / information-set model failure**，不是 outer-bound 数学公式在其假设下被 synthetic counterexample 推翻。

根因：相邻 offset-native closes 在 session boundary 并不总是一个完整 native bar的 endpoints；冻结模型错误地把 slicer 丢弃的 partial-bar交易分钟也归入当前 bar OHLC envelope。

## 6. 下一步

若继续，只允许 results-blind **session-aware native information-set / structural-bounds preanalysis**：显式区分 complete native bars、discarded partial-bar gaps、午休/隔夜 transition，并为每一段使用真正可观测 OHLC information set。

禁止通过删除 session-boundary legs、经验缩窄 bounds、拟合 proxy 或改变 same-event matcher 来绕过失败。只有 session-aware model 先通过 data-consistency/coverage gates，才有资格再次讨论 identifiability/tightness。

当前全局状态仍为：`morphology_replication_not_yet_accepted`。
