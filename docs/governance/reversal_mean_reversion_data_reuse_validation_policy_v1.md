# 广义反转 / 均值回归：数据复用与验证政策 v1

日期：2026-09-08

状态：**prospective authority / 不追溯改写已经冻结并执行的历史裁决**

## 1. 核心原则

本项目明确采用三层数据角色：

1. **TRAIN / Research corpus（训练/研究集）**
2. **VALIDATION / Diagnostic validation（验证集）**
3. **BLACKBOX / Confirmation reserve（黑箱确认集）**

最重要的原则是：

> **数据本身不是一次性消耗品。**
>
> 真正会被消耗的是某段数据“从未被研究者看过、因此可作为独立黑箱确认”的资格。

因此，已经看过的数据仍然可以长期重复用于训练、机制研究、诊断、参数估计、错误分析和后续版本开发；不得把它描述成“失效数据”或“不能再用的数据”。

---

## 2. TRAIN / Research corpus

用途：

- 发现现象；
- 构造特征；
- 设计模型；
- 调整低容量参数；
- 做误差分析；
- 拆事件、拆年份、拆方向、拆市场状态；
- 对失败样本做细节研究；
- 反复训练和重跑。

允许完全查看：

- row-level 数据；
- event-level outcome；
- 年份、方向、分层统计；
- 模型残差；
- 失败案例；
- 参数敏感性。

TRAIN 可以反复使用，不存在“今年用过明年就不能用”的规则。

---

## 3. VALIDATION / Diagnostic validation

用途：

- 检查训练得到的机制/模型是否能跨时期维持；
- 检查是否只在 TRAIN 某一阶段碰巧成立；
- 检查 calibration、稳定性和结构性失败。

VALIDATION 与黑箱不同：

> **验证结果出现问题时，允许打开细节研究原因。**

允许查看：

- aggregate metrics；
- 年度/季度/方向/状态拆分；
- event-level 失败；
- 误差来源；
- 数据质量问题；
- 具体 regime / market-condition breakdown。

VALIDATION 可以反复使用，并且可以根据验证结果继续开发下一版模型。

因此一旦某个数据块被用于详细诊断，它仍然是有价值的 VALIDATION / research data，只是不再有资格被称为“完全未见的 BLACKBOX”。

---

## 4. BLACKBOX / Confirmation reserve

BLACKBOX 的作用只有一个：

> **在模型、参数、边界和评价方法全部冻结后，做一次真正独立的最终确认。**

### 允许输出

原则上只允许事前定义的 aggregate 结果，例如：

- total sample count；
- frozen primary metric；
- frozen benchmark comparison；
- pass / fail / insufficient；
- 必要的 data-integrity gate。

### 默认禁止输出

- event 日期；
- event path；
- 哪一年最好/最差；
- long/short 细分；
- regime 分层；
- 失败样本；
- 参数敏感性；
- 能帮助研究者针对该 block 修改策略的诊断信息。

### 黑箱失败怎么办

有两种合法选择：

**A. 保持黑箱身份**

只接受 pass/fail 结果，不打开细节。之后若有独立原因产生新版本，可按另一个事前协议再次评估；不得根据隐藏细节定向修补。

**B. 主动解封并诊断**

如果决定“我要知道为什么失败”，则允许打开事件和细节；但从打开那一刻起：

`BLACKBOX -> VALIDATION`

该数据块以后可以反复研究，但不能再被称为独立黑箱确认集。未来若需要真正独立 confirmation，再分配一个新的 BLACKBOX block。

这不是数据作废，而是**证据角色变化**。

---

## 5. 本仓当前数据角色

现有 2015-2020 数据从现在起解释为长期可复用研究资产：

- `2015-01-05 .. 2018-12-31`：`TRAIN / research corpus`
- `2019-01-01 .. 2020-12-31`：`VALIDATION / diagnostic validation`

它们都已经被研究过程查看，因此：

- 不再称 fresh；
- 但仍可无限次用于新的 TRAIN/VALIDATION 研究；
- 新机制可以在这里做开发和诊断，只需诚实标记为 reused evidence；
- 不需要为了每条新机制重新寻找一套完全没看过的数据。

当前尚未在本政策下正式指定新的 BLACKBOX 日期区间。

新的 BLACKBOX 只在：

1. 新数据完成 source/provenance admission；
2. 研究方向已经在 TRAIN + VALIDATION 上基本定型；
3. 候选、参数、评价指标和停止规则均已冻结；

之后才分配。

---

## 6. 样本 gate 的新原则

未来不再默认使用“每个自然年必须 >= N 个事件”的机械规则，除非该年级稳定性本身就是明确研究问题。

默认优先采用：

- TRAIN 总有效样本量；
- VALIDATION 总有效样本量；
- 至少跨两个时间段的稳定性；
- 事前定义的统计精度 / 最小可检测差异；
- 必要时再报告逐年稳定性作为诊断。

不能为了某次结果临时降低样本门槛，但可以在**下一研究 identity 结果打开前**根据事件基准率和统计精度重新设计合理的样本门。

### 历史 T1 不追溯改写

T1 的 `2019 aligned 48 < frozen 50` 是在旧协议下事前冻结并执行的结果，因此该次 identity 保持：

`CLOSED_BEFORE_OUTCOME`

本新政策不能倒过来把历史 T1 判成通过。

但未来新的 theory identity 不再自动继承“每年 50”这种门槛。

---

## 7. 为什么这样更节省数据

正确的资源分配是：

- **大部分历史数据**长期放在 TRAIN + VALIDATION，反复研究；
- **很少一部分最新且足够长的数据**留作 BLACKBOX；
- BLACKBOX 只给已经成熟的候选使用，不给每个想法使用。

因此策略方向发现阶段不会不断“烧掉年份”。

真正稀缺的是独立确认资格，不是历史行情本身。

---

## 8. 对本仓后续工作的约束

以后任何研究必须同时声明：

- 哪些数据属于 TRAIN；
- 哪些属于 VALIDATION；
- 是否使用 BLACKBOX；
- 如果使用 BLACKBOX，允许返回哪些 aggregate outputs；
- 是否发生过 BLACKBOX -> VALIDATION 的主动解封。

不得把 TRAIN/VALIDATION 结果包装成 fresh OOS。

也不得为了追求“永远 fresh”而拒绝合理重复使用历史数据。

Production authority = false。
