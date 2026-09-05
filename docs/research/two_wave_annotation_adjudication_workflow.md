# 两浪 H0 双人标注与争议仲裁

本工具实现冻结评价协议中的标注来源记录、两位审查者意见对照和显式仲裁。它不生成真实标签，不修改识别公式、±2 根容差或验收门槛；运行后仍为 `morphology_replication_not_yet_accepted`。下面提到的真人、独立性和完成声明均须由实际审查过程支持，字段校验不能证明声明是真的。

## 1. 先独立审查，再补齐来源声明

审查者 A/B 分别使用预先抽取的同一产品、同一尺度、同一核心窗口。首次独立审查不能看到算法结果或对方意见。离线与在线分别提交；已看过该样本未来的人不能担任其盲在线审查者。在线要保留相同截止 bar 和信息时钟；`bar_end` 只表示理想同步前缀，不证明历史 PIT。

在现有盲回放中选点、填分类并导出 JSON 后，运行：

```bash
python scripts/reconcile_two_wave_annotations.py --prepare-review reviewer_a_replay_export.json --output cloud_results/reviewer_a_preparation_v1
```

输出的 `review_to_complete.json` 保留原始标注、审查窗口和算法曝光标记，并补充尚未签署的字段。审查者要填写根级 `instrument` 与 `reviewer`，以及 `provenance`：

| 字段 | 实际含义 |
|---|---|
| `source_type` | 只有真实独立人工审查才能填 `independent_human`；算法、模型、合成资料不能冒充 |
| `reference_version` | 人工参考版本，如个人工作流的第一个版本；修订另起版本并保留旧文件 |
| `completed_at` | 完成时间，带时区的 ISO8601 字符串 |
| `blinded_to_algorithm` | 确实未见算法点/分类/候选时才填 `true` |
| `independent_of_other_reviewer` | 确实未参考另一标注者意见时才填 `true` |
| `future_exposed` | 在线参考必须确实未见截止之后价格，才填 `false` |
| `online_clock` | 在线填 `bar_end` 或 `information_available_time`，两种不能混合匹配 |

每条标注另填 `reason`（实际判断理由）和 `confidence`（0 到 1）。根级来源声明会被记录继承；某条或某窗口若来自不同审查会话，可保存其自己的 `provenance`。不要为通过校验而修改真实的曝光记录：`algorithm_visible=true` 和 `independent_reference=false` 始终阻断该记录成为独立参考。

现有回放导出已保存 `config_id/timeframe/scale_id`；它们必须维持实际 DataHub 产品和尺度身份。`visible_cutoff`、五点、相位等仍遵守原注释格式。可以同时提交多个产品/尺度，但在线身份还包含截止 bar 与声明的信息时钟，不跨这些身份匹配。

只想准备空表时：

```bash
python scripts/reconcile_two_wave_annotations.py --empty-templates --output cloud_results/two_wave_annotation_workflow
```

这会生成 `reviewer_a_empty.json`、`reviewer_b_empty.json` 和 `decisions_empty.json`。空表不包含人工标签，也不声明已经完成窗口审查。双方真实标注文件就绪后才进入下一步。

## 2. 生成争议清单

```bash
python scripts/reconcile_two_wave_annotations.py --reviewer-a reviewer_a_v1.json --reviewer-b reviewer_b_v1.json --output cloud_results/two_wave_reconciliation_v1
```

输出包括：

- `reconciliation.json`：每条双方原始意见、来源缺项、未匹配对象、分类分歧、容差内几何偏移、待决状态和窗口排除原因。
- `decisions_template.json`：逐案空仲裁表，与两个输入的规范 JSON 内容 SHA-256 绑定。
- `adjudicated_reference.json`：兼容 `two_wave_annotations@1.0` 的参考文档。未经显式仲裁的对象不会进入其中；首次运行通常为空。

匹配复用既有最大匹配数、最小总五点距离、稳定 ID 消歧实现。每个对应极值都须在 ±2 根内，分类不参与配对。结构使用五点，完整周期使用三点；相位不混合。两位审查者结论相同也只记为“双人一致”，仍须显式签署哪个原始记录成为规范参考，避免程序自行选择几何真值。未匹配的单边对象会保留为独立案件。

## 3. 人工签署仲裁

在生成的决策表里，实际仲裁者填写：

| 字段 | 允许内容 |
|---|---|
| `action` | `accept_a` / `accept_b` / `reject_both` / `ambiguous`；`null` 继续待决 |
| `adjudicator` | 实际执行仲裁的人的稳定身份；不要求凭空增加第三个人 |
| `decided_at` | 带时区完成时间，不得早于相关初次审查完成时间 |
| `reason` | 选择、排除或仍不能确定的实际理由 |

`accept_a/accept_b` 仅选择已有的、来源合格的原始记录；缺来源、已曝光或原始标记歧义的记录不能靠一个签名自动变合格。几何修正需要真实审查者提交新版本源文件，重新生成清单和决策。`reject_both` 保留明确排除记录；`ambiguous` 保留歧义并继续计入未解决数量，不隐藏删除。若不同案件的人工作出选择后生成了同一参考视图中的重复五点，工具会报错并要求明确修订决策，避免重复截图提高样本量。

```bash
python scripts/reconcile_two_wave_annotations.py --reviewer-a reviewer_a_v1.json --reviewer-b reviewer_b_v1.json --decisions decisions_signed_v1.json --output cloud_results/two_wave_adjudicated_v1
```

输出目录必须全新或为空，避免覆盖早期审查和仲裁。源文档改变会改变哈希，旧仲裁表不能静默应用到新意见。保留原始输入文件、原始回放导出、抽样清单和所有版本的决策表。

## 4. 完整窗口与仍需完成的验收

只有双方同一核心范围、同身份和同模式的窗口都明确完成审查，且核心内案件已解决、无来源污染时，才导出可用于主要计分的 `fully_reviewed=true` 窗口。对象归属依第五极值（完整周期为第三极值），早期成员可以落在窗口外的前文。在线窗口还须同一截止和信息时钟。`kind=all` 的完整审查同时受周期与结构的待决案件阻断。缺另一位审查者窗口、重复窗口、未完整审查、歧义或待决对象都保留在审计清单。

双方完整审查且都明确没有对象，允许保留负例窗口；仅有空表不会产生这种声明。即使某个对象从干净的 B 来源被选为参考，A 在同一核心的污染记录仍会阻断该窗成为双盲完整审查范围。该对象可以作为范围外的稀疏参考保留。

`adjudicated_reference.json` 可以送入点估计和分块 bootstrap 工具；当前 bootstrap 入口仅支持 `bar_end` 在线视图，对 `information_available_time` 在线参考会明确拒绝，后者可在本模块中记录与仲裁但须另行实现兼容其信息集的评价，不能冒充 bar-end 结果。当前原有 `evaluate_annotations` 的返回字典中“仲裁工具未实现”的旧固定说明不感知这个外部流程，不能据此推断已经或尚未实际完成人工仲裁，应同时阅读本次 `reconciliation.json`。

本模块保留歧义的数量、比例、受影响窗口和原始意见；它不替代最终“歧义计入/排除”的指标敏感性分析。正式验收仍需离线/在线分别达到冻结样本数、类别数、完整审查、独立性及不确定性要求。不能把程序测试中的构造标签、仲裁通过或两人一致率称为真实市场形态准确率；H1/H2、注册和交易权限保持关闭。
