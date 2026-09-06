# v0.6.4 predecessor-supported ordinal0 projection：正式结果与云端裁决

日期：2026-09-06

状态：`mechanism_supported_candidate_not_promoted_due_scale_evidence_multivalued_identity`

操作基线仍为 **v0.4.3**。全局状态仍为 `morphology_replication_not_yet_accepted`。本轮没有使用 D1/D2/PAWCT、收益、outcome 或交易信息，也没有修改 frozen filtered-tuple matcher、ridge linking、tuple-birth death certification 或 qualification thresholds。

## 1. 冻结候选

v0.6.4 只注册一个 repair candidate：

`birth_scale_predecessor_filtered_phase_start`

它只把 ordinal0 lower support 从：

```text
max(0, 2*f0 - f1)
```

替换为：

```text
immediate birth-level predecessor filtered extremum occurrence + 1
```

ordinal0 upper 仍为 `f1-1`；ordinals1..4 的 sequential lower / filtered upper / ordinal4 confirmation upper 全部不变。

协议在任何 v0.6.4 financial output 出现前发现并修正了一次 **hard-control transcription typo**：offset3/4 的 v0.6.2 pair/control-displaced 数字被手工抄错；修正后的协议 blob SHA 为 `624f098e49a1c502221b1e3a5c3c0e835be161c6`。该修正发生在候选 replay 之前，不是结果后改门槛。

实现 helper Git blob SHA：`3a8c80e2f9cbe55cf743108ee6028c022dec5d63`。

synthetic tests：**9/9 PASS**。

## 2. Frozen controls 全部复现

```text
filtered mutual-unique pairs: 14784 / 12725 / 13412 / 16108
control raw displaced:        6975 / 7311 / 7534 / 7453
v0.6.3 residual:              1578 / 1738 / 1806 / 1718
v0.6.1 post-tuple target:      191 / 194 / 193 / 209
v0.6.3 target residual:         32 /  28 /  30 /  32
```

无 control drift。

## 3. Cross-view strict identity：四个 offset 全部净改善

Control strict pairs：

```text
offset1 7,638
offset2 5,188
offset3 5,593
offset4 8,332
aggregate 26,751 / 57,029 = 46.91%
```

Candidate strict pairs：

```text
offset1 8,381  (+743)
offset2 5,770  (+582)
offset3 6,204  (+611)
offset4 9,098  (+766)
aggregate 29,453 / 57,029 = 51.65%
```

净增加 **2,702 strict pairs**，四个 harmless offsets 全部同向改善。

## 4. Repair / damage accounting

29,273 个 frozen control raw-displaced pairs：

- repaired to candidate strict: **3,986 = 13.62%**
- unchanged displaced: **25,235**
- newly invalid/censored: **49**
- candidate multi-valued pair: **3**

26,751 个 frozen control strict pairs 中：

- newly broken: **1,399 = 5.23%**

所以这不是“只增加覆盖”：candidate 的 repaired 数明显大于 newly broken，且四个 offset 的净 strict count 都上升。ordinal0 predecessor support 确实捕捉到了 v0.6.3 所定位的真实机制。

## 5. v0.6.3 residual stratum：修复约三分之一

6,840 个 canonical-1m residual：

- repaired: **2,390 = 34.94%**
- unchanged displaced: 4,431
- newly invalid/censored: 17
- candidate multi-valued: 2

逐 offset repaired：

```text
652 / 1578
540 / 1738
552 / 1806
646 / 1718
```

因此 predecessor support 对最直接的 phase-window residual 有明显解释和修复能力，但不是完整解法；v0.6.3 已单列的 sequential-lower 等问题仍然存在。

## 6. v0.6.1 target：总体修复有限，target residual 上更明显

原 v0.6.1 `post_tuple_birth_loss` 中 787 个 projection-displacement targets：

- repaired: **80 / 787 = 10.17%**
- unchanged displaced: 707

其中 v0.6.3 仍在 canonical-1m 下 displaced 的 122 个 target residual：

- repaired: **50 / 122 = 40.98%**
- unchanged displaced: 72

这与前序诊断一致：787 个 target 中大量问题是 5m sampling lattice aliasing，ordinal0 support repair 只应主要作用于 canonical-1m residual 部分，不应被期待修复所有 787 个。

## 7. Candidate validity 比 control 更好，但不是 promotion 决定因素

五个视图 candidate `no_valid_candidate_projection`：

```text
458 / 438 / 442 / 455 / 424
```

主要仍是 `raw_projection_not_actual_turn`；明确 `ordinal0_left_censored_no_predecessor` 仅：

```text
7 / 8 / 8 / 8 / 8
```

所以“真实 predecessor 不存在”并没有制造大面积覆盖损失。

## 8. 决定性失败：canonical filtered identity 被 birth-scale evidence 重新多值化

五个视图**每个恰好出现 1 个**：

`multi_valued_candidate_projection`

这些 group 都具有同样结构：

- canonical filtered tuple 的五个 filtered occurrence anchors 完全相同；
- group 有两个不同 birth-scale evidence members；
- 两个 birth level 的 immediate predecessor 不同；
- 两个 candidate raw identities 只在 ordinal0 分叉，ordinals1..4 相同。

例如 offset0 的同一 canonical filtered tuple：

```text
filtered times:
2018-05-24 05:10 / 05:15 / 05:45 / 06:00 / 06:15 UTC

candidate raw identities:
[39560, 39562, 39570, 39571, 39574]
[39563, 39564, 39570, 39571, 39574]
```

offset1..4 也各有同型实例。

数量上只有 5 个 group，比例极小；但这是**定义级失败，不是频率问题**。

v0.6.0 已冻结：birth scale 是 canonical financial identity 的 evidence，不是 identity key。一个 later scale evidence 不得把已经发布的 financial identity 改成另一个 raw event。

而 v0.6.4 candidate 的 ordinal0 support 直接读取“当前 member 的 birth level predecessor”，因此相同 canonical filtered identity 可以因为 evidence level 不同而映射到不同 raw identity。

这违反了我们已经冻结的 append-only / identity semantics。

## 9. 正式裁决

v0.6.4 得到两个同时成立的结论：

1. **Mechanism supported**：真实 predecessor support 在四个 offsets 上都提高 strict identity，并修复 34.94% v0.6.3 residual；v0.6.3 对 ordinal0-left 的机制定位成立。
2. **Candidate not promoted**：`birth_scale_predecessor_filtered_phase_start` 不是 canonical filtered identity 的单值函数，因为 birth-scale evidence 会改变 predecessor/raw ordinal0。

因此 v0.6.4 **不得进入 downstream qualification audit，也不得替换 frozen `project_event_to_raw`**。

## 10. 下一步：scale-invariant predecessor identity

下一步必须另开新版本，不能在 v0.6.4 结果后追加第二个规则。

最直接需要研究的是：

> canonical filtered identity 一旦首次发布，ordinal0 predecessor/raw support 是否也应由**首次 causal tuple-birth evidence**一次性冻结；later same-anchor scale evidence 只能追加 evidence，不能重新投影 financial identity。

这把 v0.6.0 已经验证过的原则：

`first qualified evidence publishes immutable identity; later scale evidence appends only`

上移到 filtered-parent → raw-projection identity 层。

下一版本必须先写 preanalysis/frozen protocol，再实现；不得选“最匹配另一个 offset”的 evidence member。

## 11. 当前状态

`morphology_replication_not_yet_accepted`

操作基线仍为 v0.4.3。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading 和 production 全部继续冻结。
