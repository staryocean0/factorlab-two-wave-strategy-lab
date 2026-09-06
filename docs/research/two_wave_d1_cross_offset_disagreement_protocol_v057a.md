# v0.5.7a D1/D2 cross-offset disagreement attribution protocol（结果前冻结）

日期：2026-09-06  
状态：`read_only_attribution_protocol_frozen_no_new_classifier`

## 1. 已知事实与本协议边界

本协议是在 v0.5.6 已被正式 multiview hard gate 否定之后冻结，因此**已知**：

- v0.5.6 main5m mechanism PASS；
- D2 18/18 prefix causality PASS；
- D1/D2 selected intervals 完全相同；
- D2 same-label fraction 在四个 native offset 上全部低于 D1，平均约 -3.18pp。

本协议不伪装成对“D2 是否失败”的预注册；失败已经发生。

本协议只预注册**失败归因**，在任何 v0.5.7 新分类器之前解释：

> D2 的跨 offset label-agreement 损失究竟来自哪里？

本阶段不运行 recognizer、不修改任何 label、不搜索阈值、不看收益。

## 2. 数据与证据源冻结

只读复用 v0.5.6 正式 five-view run：

- source run：`34009427027`
- source execution commit：`266bac6389098169598084667fcb46897a53ccf2`
- 五个已成功 native-view artifacts：
  - offset_0 `9982054238`
  - offset_1 `9982052651`
  - offset_2 `9982053168`
  - offset_3 `9982051672`
  - offset_4 `9982051902`

这些 artifact 已证明每个 view 的 full+25/50/75% prefix zero rewrite；本阶段不得重跑 recognizer 以产生不同对象。

映射只使用仓库已供应 `1m_official` 的**时间戳**作为共同时间轴，不合成/重采样价格。

## 3. Stage A：纯 label transition attribution

对每个 `offset_i, i=1..4`，仅在主视图与该 offset 的**共同 selected-owned 1m bars**上比较：

- `D1_agree = main_D1 == other_D1`
- `D2_agree = main_D2 == other_D2`

将每个共同拥有 bar 分成互斥四类：

1. `both_agree`：D1 agree 且 D2 agree
2. `D2_harm`：D1 agree 且 D2 disagree
3. `D2_help`：D1 disagree 且 D2 agree
4. `both_disagree`：D1 disagree 且 D2 disagree

有恒等式：

`D2_agreement - D1_agreement = (D2_help - D2_harm) / common_owned_bars`

脚本必须逐 offset 验证该恒等式与 v0.5.6 failure diagnostic 的正式 delta 精确一致（浮点容差只作数值保护）。

## 4. 预冻结的核心归因问题

### A. `D2_harm` 是否主要来自 D1 uncertain 的不一致解析？

统计 `D2_harm` 中 D1 共同标签：

- uncertain
- range
- uptrend
- downtrend

尤其报告：

`P(D1共同标签=uncertain | D2_harm)`。

若该比例高，说明 D2 的主要稳健性代价可能不是“把稳定趋势翻错方向”，而是**把原来跨 offset 一致保留为 uncertain 的对象，解析成不同的明确状态**。

### B. D2 如何把一个 D1-agreed label 分裂？

对 `D2_harm` 输出三元 transition：

`(shared_D1_label, main_D2_label, other_D2_label)`

报告 top transitions，方向顺序保留，不把 up/down 合并。

### C. D2 的收益发生在哪里？

对 `D2_help` 输出：

`(main_D1_label, other_D1_label, shared_D2_label)`

并与 harm 数量对照。不能只报告 harm。

### D. range 是否是主要不稳来源？

分别统计 main/other D2 labels 中 range 涉及的 harm/help bar 数；不能因为 v0.5.6 main5m range 增加就预设 range 是失败根因。

### E. low/high phase 暂不在 Stage A 推断

coverage artifact 不含完整几何 feature，Stage A 不得从 label transition 猜 phase、margin 或 endpoint 机制。

## 5. Record-pair weighting

bar-level attribution 是正式主口径，因为原 multiview hard gate 就是共同拥有 1m bars 的 same-label fraction。

同时输出 record-pair 辅助口径：

- 每个主 selected interval 与 other selected interval 的非空时间交集为一个 pair；
- pair 权重 = 共同 1m bars 数；
- 输出 harm/help pair 数及其权重分布；
- 不用 pair-count 替代 bar-weighted 正式口径。

## 6. Stage A 决策规则

Stage A 完成后：

- 若 >50% 的 `D2_harm` 来自 shared D1=`uncertain`，下一步优先做**uncertain-resolution instability** 的 Stage B geometry attribution；
- 若主要来自 shared D1 明确 trend/range，下一步优先审计 D2 对已稳定标签的破坏机制；
- 若 harm 高度集中于少数 record pairs，先做 endpoint/boundary case-pair audit；
- 若 harm 广泛分散，则做全体 geometry margin attribution。

50% 只用于选择**下一诊断分支**，不是接受/拒绝任何分类器的性能阈值。

## 7. Stage B（本协议只定义输入，不执行新分类）

Stage A 后若需要几何归因，才允许重新构建 frozen v0.5.4/v0.5.6 records，但只能读取特征：

- `s0/s1/s2`
- `E_upper/E_lower`
- 各自距 ±0.15 的 margin
- `net=s0+s1`
- phase low/high
- five occurrence timestamps 与跨 offset endpoint displacement
- amplitude unit / amplitude ratio
- birth scale level / sigma
- cycle durations / leg durations
- corresponding-leg duration diagnostic

Stage B 仍不得产生新 label。

## 8. 明确禁止

本归因阶段禁止：

- 修改 `phase_tolerance=0.15`
- 修改 D1 或 D2 公式
- 新建 D3/v0.5.7 classifier
- 根据案例挑选新阈值
- 使用 future returns / H1/H2 / P&L
- 回头修改 v0.5.2 parent 或 v0.5.4 qualification

## 9. 输出

必须保存：

- source run / artifact IDs / execution commit
- 每 offset common-owned bars
- formal D1/D2 agreement 与 delta 复核
- four-way category counts/fractions
- D2_harm shared-D1 label 分布
- D2_harm transition matrix
- D2_help transition matrix
- range-involved harm/help
- record-pair weighted diagnostics
- 下一诊断分支选择及其证据

状态固定为：

`read_only_cross_offset_disagreement_attribution_not_classifier_result`
