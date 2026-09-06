# v0.6.5 scale-invariant predecessor/raw publication：正式结果与云端裁决

日期：2026-09-06

状态：`structural_publication_pass_downstream_qualification_audit_authorized`

操作基线仍为 **v0.4.3**。全局状态仍为 `morphology_replication_not_yet_accepted`。本轮没有修改 predecessor geometry、ridge、tuple birth、qualification、matcher、direction、packing、outcome 或 trading logic。

## 1. 冻结候选

v0.6.5 只改变 v0.6.4 candidate evidence 的发布语义：

`first_valid_causal_predecessor_projection_publication`

同一个 canonical filtered identity `(phase, five filtered bars)` 的 tuple-birth evidence 按：

`(birth_confirmation_bar, birth_level, event_id)`

严格排序。第一个 v0.6.4 predecessor-supported projection 有效的 evidence 一次性发布 immutable raw identity；此前 invalid evidence 只保留失败记录；later same-anchor evidence 只 append，不允许重新投影或改写已发布 raw identity。

没有使用 cross-view similarity、D1、qualification、return 或 outcome 选择 publisher。

## 2. Synthetic gate

新增 append-only publication tests：**9/9 PASS**。

覆盖：

- first valid immediate publication；
- invalid-before-valid；
- all-invalid no publication；
- later same identity append；
- later divergent raw identity 被标记 `later_valid_would_rewrite_suppressed`；
- confirmation tie 按 birth level / event ID；
- prefix publication event == full publication event；
- future evidence append 不改写；
- API 中不存在 cross-view similarity 输入。

## 3. Frozen hard controls 全部复现

```text
filtered mutual-unique pairs: 14,784 / 12,725 / 13,412 / 16,108 = 57,029
current-control raw strict:     7,638 /  5,188 /  5,593 /  8,332 = 26,751
current-control raw displaced:  6,975 /  7,311 /  7,534 /  7,453 = 29,273
v0.6.3 residual:                1,578 /  1,738 /  1,806 /  1,718 = 6,840
v0.6.1 projection targets:        191 /    194 /    193 /    209 = 787
v0.6.3 target residual:             32 /     28 /     30 /     32 = 122
```

v0.6.4 candidate strict control也复现：

`8,381 / 5,770 / 6,204 / 9,098 = 29,453`。

## 4. Per-view publication：定义级多值消失

| view | canonical filtered groups | published single identity | no valid publication | suppressed would-be rewrite |
|---|---:|---:|---:|---:|
| offset0 | 38,634 | 38,176 | 458 | 1 |
| offset1 | 37,175 | 36,737 | 438 | 1 |
| offset2 | 37,061 | 36,619 | 442 | 1 |
| offset3 | 36,935 | 36,480 | 455 | 1 |
| offset4 | 36,688 | 36,264 | 424 | 1 |

v0.6.4 每个视图的 1 个 `multi_valued_candidate_projection` 均被 v0.6.5 收口成一个 immutable published identity。

五个历史案例每个都记录了 exactly one later divergent evidence，并各自得到：

`suppressed_would_be_rewrite_count = 1`。

因此总计 **5 次 would-be rewrite 被 append-only publication 阻止**。

## 5. Cross-view structural result：v0.6.4 的改善完整保留

v0.6.5 published strict：

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453 / 57,029 = 51.65%
```

与 v0.6.4 candidate strict **逐 offset 完全相同**；`published_strict_delta_vs_v064 = 0`。

相对 frozen current control：

`29,453 - 26,751 = +2,702 strict pairs`。

四个 harmless offsets 均保持正向净改善。

## 6. v0.6.4 multi pair 的处理没有择优

v0.6.4 的 5 个 multi-valued cross-view pair 在 v0.6.5 中全部按 first-valid publication 被归入：

`v064_multi_to_displaced = 5`。

没有为了提高 match count 从 later evidence 中挑更匹配另一 view 的 raw identity。

这是预期的治理行为：**宁可保留失配，也不能让跨视图结果参与单视图 financial identity 发布。**

## 7. Current-control transition accounting

Aggregate：

- repaired: **3,986**
- unchanged displaced: 25,238
- retained strict: 25,328
- newly broken: **1,401**
- newly missing publication: 714
- control-invalid → published strict: 139
- control-invalid → published displaced: 223

相较 v0.6.4，`newly broken` 多 2，是因为两个原先被标成 multi 的 control-strict pair 现在必须使用 first-valid immutable publication，结果为 displaced；没有隐藏或择优消除这些失败。

即使如此，总 strict count 仍与 v0.6.4 完全一致，且相对 current control 净增 2,702。

## 8. Frozen difficult strata：v0.6.4 repair signal 保留

v0.6.3 canonical-1m residual 6,840：

- repaired **2,390**
- unchanged displaced 4,433
- no publication 17

v0.6.1 projection-displacement targets 787：

- repaired **80**
- unchanged 707

v0.6.3 target residual 122：

- repaired **50**
- unchanged 72

这些 decisive repair counts 与 v0.6.4 保持一致；原两个 residual multi case 现在被诚实计入 unchanged displaced。

## 9. 正式裁决

v0.6.5 **通过 structural publication gate**：

1. raw identity 对 canonical filtered identity 已变成 append-only 单值发布；
2. later scale evidence 不能改写；
3. 五个已知 v0.6.4 multi-valued examples 全部闭合；
4. 不使用 cross-view information 选择 evidence；
5. v0.6.4 四-offset 结构净改善完整保留。

因此 v0.6.4 的 predecessor mechanism 可以继续研究，但 v0.6.5 仍不是 accepted recognizer，也不能直接替换生产 `project_event_to_raw`。

按冻结协议，唯一新授权是：

> **可以另开一个结果前冻结的 downstream v0.5.4 qualification audit，验证这个新定义的 published raw identity 在 harmless slicing 下是否具有稳定的 qualification survival。**

## 10. 仍未解决

- v0.6.3 的 sequential-lower residual 仍独立存在；
- upstream filtered-extremum / tuple-topology instability 未被 v0.6.5 修复；
- qualification stability 尚未验证；
- direction/D1/D2/PAWCT 继续冻结。

当前状态仍为 `morphology_replication_not_yet_accepted`，操作基线仍为 v0.4.3。
