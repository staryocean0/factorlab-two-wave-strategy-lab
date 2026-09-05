# v0.5.2 frozen qualification rejection attribution 协议

日期：2026-09-06  
状态：`diagnostic_protocol_frozen_before_result`

## 1. 目的

v0.5.2 parent identity 已通过；v0.5.3 birth-scale TCSS leg-efficiency 假说已在主 5m 被否定。

本轮**不是新策略版本**，不修改任何 qualification 公式或阈值，只回答：v0.5.2 的 38k 级 parent candidates 究竟被哪些 frozen rules 阻塞，以及这些阻塞是独立还是共现。

## 2. 冻结内容

完全复用 v0.5.2：

- TCSS；
- extremum ridges；
- exact five-ridge tuple birth；
- raw projection；
- v0.4.3 qualification；
- D1；
- deterministic ledger。

不运行收益、交易、H1/H2，不更改 `min_leg_efficiency=0.5`、`duration_ratio=2.0`、jump / amplitude 等任何阈值。

## 3. 必须输出

主视图 `5m_offset_0` 上：

1. 每个 rejection reason 的总出现次数；
2. 每个 reason 的 exclusive-only count；
3. counterfactual `remove-this-reason-only` 可新增 qualified 数（等价于 exclusive-only，但单列确认）；
4. 每个 candidate 的 rejection-count 分布；
5. rejection reason pair co-occurrence：count / Jaccard / lift；
6. 对 exactly-one-reason near-pass candidates，按 reason 统计 birth-scale level、cycle-duration ratio、corresponding-leg duration ratio、min raw ER、max jump share 的分布；
7. 2018-06-20、2019-04-15、2020-07-15 固定窗口 rejection chain；
8. 若 legacy fixed cases 文件存在，审计 case_00 / 02 / 11 / 14；不存在则明确标记，而不是猜测。

## 4. 解释约束

- 最大总拒绝数不等于首选修改项；高度共现的规则可能只是同一坏结构的不同症状。
- 首选下一项单组件必须优先来自：**exclusive near-pass 数量 + fixed-window mechanism + 与 parent-scale 语义是否一致**。
- 不以“移除后 candidate 更多”本身作为成功标准。
- 不根据本轮结果直接调阈值；本轮只能生成下一轮的结果前假说。
