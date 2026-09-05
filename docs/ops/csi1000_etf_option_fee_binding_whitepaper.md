# ETF期权手续费与合约单位绑定白皮书

> 四层归属：`4 执行标的/账户测试`。当前统一入口见 [`timing_layer4_execution@1.0`](timing_layer4_execution_registry@1.0.json)。

状态：用户权威费率和合约单位已闭合；DataHub ETF期权盘口固定版本仍未完成。

一张ETF期权对应10,000份ETF。报价单位为每份ETF的人民币价格，因此一张权利金现金为`quote_price × 10,000`。普通买入或卖出交易费为每张每边4.5元；完成一次买入再卖出的普通往返为每张9元。

本合同不推断行权、指派、过户或到期结算费。需要进入行权/指派的路径必须fail closed，直到用户另行冻结合同。

手续费只是成本参数，不提供行情。DataHub当前完成了原始预取并生成部分物化/性能证据，但正式候选、primary acceptance、READY successor和exact research serving尚未完成。因此当前可以计算给定价格和张数的权利金及手续费，不能据此宣称ETF期权盘口回放可用。
