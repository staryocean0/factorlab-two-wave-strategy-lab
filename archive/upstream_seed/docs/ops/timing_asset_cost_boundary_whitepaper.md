# 择时基础设施资产类别成本边界白皮书

> 四层归属：`4 执行标的/账户测试`。当前统一入口见 [`timing_layer4_execution@1.0`](timing_layer4_execution_registry@1.0.json)；本页 `@2.0` 为现役，`@1.0` 只保留历史。

## 结论

交易价格与显式成本必须分账，且成本合同不得跨资产类别搬运。

| 资产身份 | 入场/出场价格 | 唯一显式成本 |
|---|---|---|
| 股票 | 冻结股票成交合同指定的价格 | 买入1bp、卖出6bp |
| 境内股票ETF | raw/PIT成交价；另受T+1和长短权限约束 | 用户授权佣金买入1bp、卖出1bp；印花税0；不含价差/滑点/冲击/跟踪 |
| 非可交易指数信号 | 原始指数next-open仅用于信号归因 | 零；不得套股票1+6bp |
| 指数方向的个股复制成本代理 | 原始指数next-open作方向路径 | 用户授权的1bp+6bp数量级验证；非真实账户 |
| 长期权买方 | Ask买入、Bid卖出 | 14元/张/边，往返28元 |
| 短期权卖方 | Bid卖出、Ask买回 | 14元/张/边，往返28元 |

Bid/Ask本身就是成交价，不是另一项要从收益里重复扣除的成本。价差、波动率和时间价值已经体现在入场价与出场价之差中。当前股指期权回测只允许在该价格收益上再扣固定手续费。

## 事故来源

`csi1000_medium_frequency_limited_history_v1`把股票的1bp入场＋6bp退出写入非可交易指数信号账本，并用扣费后的指数收益参与频段选择。虽然每次费率统一，但高频交易次数更多，累计扣费不同，因此会改变频段排名。该V1的选频、指数净收益排名及基于其终点策略的继任结论全部撤权。

MO同步L1执行器没有该错误：长期权一直是Ask买入、Bid卖出，显式成本只有14+14元。问题发生在上游指数信号选频层。

## 机器硬门

实现`timing_asset_cost_boundary@2.0`提供五个不可互换合同：

- `equity_entry1bp_exit6bp@1.0`
- `stock_etf_commission_1bp_each_side_t1@1.0`
- `nontradable_index_signal_zero_explicit_cost@1.0`
- `market_index_equity_replication_1bp_6bp_sensitivity@1.0`
- `MO_long_option_ask_entry_bid_exit_CNY14_per_side@1.0`
- `MO_short_option_bid_entry_ask_exit_CNY14_per_side@1.0`

`event_cost_log()`要求调用者同时声明资产类别；股票合同传给指数信号会直接抛出`ValidationError`。期权合同把Bid/Ask登记为价格字段，并把`explicit_cost_components`冻结为仅`fixed_fee`。

## 研究分层

1. 指数层用零显式成本回答纯信号问题；在用户明确授权时，可另建独立命名的7BP个股复制成本代理验证。
2. MO层回答能否交易，使用实际Bid/Ask成交价格，再扣14元/边。
3. 不能把指数毛收益或7BP复制代理称为可交易指数收益或已实现个股收益。
4. 若MO L1不完整，必须报告测量缺口；不得用7bp或代理价差替代。

## 当前权限

V1注册表保留历史四合同，`current=false`，`superseded_by=@2.0`。当前唯一机器注册表为`timing_asset_cost_boundary_registry@2.0.json`：在V1四合同上增加股票ETF佣金身份和指数个股复制敏感性代理。该基础设施只约束口径，不授予策略选择或生产权。
