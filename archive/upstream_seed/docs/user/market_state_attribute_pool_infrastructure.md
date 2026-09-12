# 市场状态属性池基础设施入口

这是公共K线属性、频谱时序、论文核响应、载体关系和衍生品执行数据的统一管理
入口。它管理数据身份、来源、哈希、状态、缺口和更新，不把任何属性直接升格为
策略信号。

## 五位一体

| 角色 | 权威入口 |
|---|---|
| 文档 | 本文：面向使用者的池边界与消费顺序 |
| 白皮书 | [`../ops/market_state_attribute_pool_infrastructure_whitepaper.md`](../ops/market_state_attribute_pool_infrastructure_whitepaper.md) |
| 代码 | `src/factor_lab/market_state/attribute_pool_infrastructure.py` |
| 测试 | `tests/unit/test_market_state_attribute_pool_infrastructure.py` |
| 工作流 | [`market_state_attribute_pool_update_workflow.md`](market_state_attribute_pool_update_workflow.md) |

机器注册表：
[`market_state_attribute_pool_registry@1.0.json`](../ops/market_state_attribute_pool_registry@1.0.json)。
第 5 池高阶字段合同：
[`market_state_derivatives_execution_pool_workflow.md`](market_state_derivatives_execution_pool_workflow.md) →
[`../ops/market_state_derivatives_execution_pool_whitepaper.md`](../ops/market_state_derivatives_execution_pool_whitepaper.md)。

## 五个池

1. `core_kline_attribute`：只放载体自身的公共K线属性。
2. `multiband_spectral_timeseries`：带通分量、RMS、能量、邻频和因果相位。
3. `paper_kernel_response`：第14工具16尺度论文核实现毛响应；不是自相关系数。
4. `carrier_relationship`：两两相关、Beta、残差趋势与领先滞后。
5. `derivatives_execution`：期货/期权基差、展期、持仓、隐波、Greeks和成本。

普通收益自相关属于核心K线属性；完整频带矩阵和论文核响应不得复制进核心池。
跨池指标通过source id和manifest关联，不靠重复列拼接。

## 消费顺序

```text
先读 current.json
  -> 找 snapshot_id
  -> 读 snapshots/<id>/catalog.json
  -> 按 pool_id 读 pools/<pool_id>.json
  -> 再访问原始source_path
```

catalog只做只读索引，不移动原数据。源产物继续由各自基础设施生成；本设施统一
管理它们的身份与更新血缘。

## 当前V1快照

```text
snapshot_id: snapshot-cf04e70b87e62dfd
catalog_semantic_digest: d2b8282253fcf2feb417dc0fa7092ce98310e051105b688458305ae945a4aab1
registered_sources: 69
```

- 核心K线属性池：ready，11个source；纯56列历史属性外，已登记未来Provider和DataHub 2m/3m/10m/20m固定快照绑定；
- 多频段谱系池：partial，11个source；
- 论文核响应池：partial，18个source；七载体14:00日级S1/S5/S10已就绪，完整16尺度×7×14仍待补；
- 载体关系池：partial，2个source（7载体×14视图年度关系已就绪）。
- 衍生品执行池：partial，27个source；新增G2A 116日时序测量面板`measurement_closed/forecast_no_evidence`和G2B-P`development_complete/forecast_no_evidence`状态；V1.4父池、CSI1000 router/成本子链、MO连续BBO与ETF期权费率绑定保留。ETF期权固定版本盘口仍等待DataHub primary acceptance和serving。

统一管理入口位于：
`artifacts/market_state/attribute_pool_infrastructure_v1/current.json`。

## 加法型Overlay

冻结的基础注册表不原地改写。新增研究基础设施通过`factorlab.market_state_attribute_pool_overlay.v1`追加到指定pool，再发布新的内容寻址snapshot。当前默认overlay为：

```text
docs/ops/market_state_attribute_pool_overlay_mo_theta@1.0.json
docs/ops/market_state_attribute_pool_overlay_csi1000_execution_v1@1.0.json
docs/ops/market_state_attribute_pool_overlay_future_kline_provider_v1@1.0.json
docs/ops/market_state_attribute_pool_overlay_csi1000_datahub_gap_closure_v1@1.0.json
docs/ops/market_state_attribute_pool_overlay_csi1000_on_demand_kline_v1@1.0.json
```

前两者把MO Theta和CSI1000日内快照路由/成本子链接入`derivatives_execution`；第三个把已支持的未来Provider接入核心K线池；最后两个分别登记MO连续BBO验收边界和DataHub正式多周期K线绑定。全部保持策略、参数、路由和生产权限关闭。

## 权限边界

- `ready`表示源文件、哈希和池合同可消费，不表示属性有效。
- `partial`表示已有可用数据但覆盖不完整。
- `planned`允许空池，必须明确缺口，不能伪称ready。
- 任何策略选择、参数、路由和生产权限均为false。

更新前必须走[更新工作流](market_state_attribute_pool_update_workflow.md)，禁止人工
修改`current.json`或覆盖旧snapshot。
