# 广义反转 / 均值回归：数据复用与验证政策 v1

日期：2026-09-08

状态：**prospective authority / 不追溯改写已经冻结并执行的历史裁决**

## 1. 核心原则

本项目采用三层数据角色：

1. **TRAIN / Research corpus（训练/研究集）**
2. **VALIDATION / Diagnostic validation（验证集）**
3. **BLACKBOX / Confirmation reserve（黑箱确认集）**

> **数据本身不是一次性消耗品。真正会被消耗的是某段数据“从未被研究者看过、因此可作为独立黑箱确认”的资格。**

已经看过的数据仍然可以长期重复用于训练、机制研究、诊断、参数估计、错误分析和后续版本开发；不得把它描述成“失效数据”或“不能再用的数据”。

## 2. TRAIN / Research corpus

用途包括：发现现象、构造特征、设计模型、调整研究参数、做误差分析、拆事件/年份/方向/状态、研究失败案例、反复训练和重跑。

允许完全查看 row-level data、event outcomes、年份/方向/分层统计、模型残差和参数敏感性。

TRAIN 可以反复使用，不存在“今年用过明年就不能用”的规则。

## 3. VALIDATION / Diagnostic validation

VALIDATION 用于检查模型是否跨时期维持，但它不是黑箱。

验证结果出现问题时，允许打开细节研究原因，包括：

- aggregate metrics；
- 年度/季度/方向/状态拆分；
- event-level 失败；
- 误差来源；
- 数据质量问题；
- regime / market-condition breakdown。

VALIDATION 可以反复使用，并可根据验证结果继续开发下一版模型。

一旦某块数据用于详细诊断，它仍然是有价值的 VALIDATION，只是不再具有“完全未见 BLACKBOX”资格。

## 4. BLACKBOX / Confirmation reserve

BLACKBOX 只在模型、参数、边界和评价方法已经比较成熟、基本冻结后才分配。

默认只输出事前定义的 aggregate 信息，例如：

- sample count；
- frozen primary metric；
- benchmark comparison；
- pass / fail / insufficient；
- data-integrity gate。

默认不输出 event 日期、路径、年份好坏、方向/状态拆分、失败案例和参数敏感性。

如果 BLACKBOX 失败后决定打开细节：

`BLACKBOX -> VALIDATION`

该数据块以后仍可反复研究。未来若仍需要真正独立 confirmation，再分配一个新的 BLACKBOX。

## 5. 当前实际角色

```text
TRAIN      = 2015-01-05..2018-12-31
VALIDATION = 2019-01-01..2020-12-31
BLACKBOX   = none
```

当前 active `R5_multiscale_serial_dependence_state_v1` 只使用 TRAIN + VALIDATION，完全不占用 BLACKBOX。

## 6. 历史“consumed / not fresh”如何解释

旧研究里的 `consumed`、`development`、`not fresh` 标签继续作为**证据身份**保留。

它们表示：这段数据已经被研究过，不能再包装成第一次独立样本。

它们不表示：

- 不能再训练；
- 不能再验证；
- 不能再拆细节；
- 必须等待新年份才能继续研究。

历史 frozen protocol / gate / adjudication 继续保留，不能因为新治理更合理就追溯改写旧实验。

## 7. 样本量政策

默认不采用“每个自然年必须 >= N”作为所有研究的通用规则。

除非逐年成立本身就是科学问题，否则优先考虑：

1. pooled effective sample size；
2. chronological stability；
3. 事前声明的精度或 minimum detectable effect；
4. 多个时间切片作为诊断。

例如历史 T1 的 `2019 48 < old gate 50` 继续是旧 identity 的真实裁决；但这个事实不能推出“2019 数据已经不能用了”，也不能自动成为未来所有 identity 的样本门。

## 8. 新数据的真正用途

新数据主要用于：

- 扩展牛/熊/震荡/高低波动状态覆盖；
- 增加稀有事件；
- 改善细路径观测质量；
- 加入 CSI300/500/1000 或全市场横截面；
- 给最终成熟候选留一小段 BLACKBOX。

新数据不是为了替换“已经用坏”的旧数据。

## 9. 权限边界

本政策允许 TRAIN / VALIDATION 上持续研究，但不授予：

- 把 TRAIN/VALIDATION 称 fresh OOS；
- 用 PnL/Sharpe 无限筛选参数；
- paper trading；
- production；
- Layer 4；
- 数据伪造、silent fill 或 repair。

Production authority = `false`。
