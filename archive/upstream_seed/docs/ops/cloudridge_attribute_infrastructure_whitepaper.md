# CloudRidge 属性基础设施白皮书

## 定位

CloudRidge 属性基础设施是 FactorLab 的公共研究资产，不属于某个 CloudRidge 滤波版本，也不属于 Residual Risk-Off 的专有因子池。它把云脊指数自身的底层 K 线属性统一为三层：

1. 属性字典：解释属性含义、高低值含义、短窗读法、长窗读法、市场结构读法、公式摘要、来源模块和使用边界。
2. 原始属性日线面板：每个交易日一行，所有属性只由该日及之前的云脊收盘序列计算。
3. 多周期均线面板：对属性面板做 MA20/50/100/200/300/400/500，服务长状态门控研究。

该基础设施不直接定义策略信号。任何策略要把属性升格为门控、打分或买卖点，必须另做事件前验证、样本外治理和图形复核。

## 实现

代码入口：

| 层级 | 路径 |
|---|---|
| Python API | `src/factor_lab/cloudridge/attributes.py` |
| 包导出 | `src/factor_lab/cloudridge/__init__.py` |
| 构建脚本 | `scripts/build_cloudridge_attribute_infrastructure.py` |
| 论文EWMA核唯一渐进式入口 | [`../user/cloudridge_paper_kernel_multiscale_timeseries_workflow.md`](../user/cloudridge_paper_kernel_multiscale_timeseries_workflow.md)；原论文位于入口Layer 0最高理论层。 |
| 论文EWMA核多尺度时序 | `src/factor_lab/cloudridge/paper_kernel.py`, `src/factor_lab/market_state/paper_kernel_multiscale_timeseries.py` |
| 单元测试 | `tests/unit/test_cloudridge_attribute_infrastructure.py` |

默认产物目录：

```text
output/cloudridge-attributes/current/
```

默认数据源优先级：

1. `output/cloudridge_full_datahub_20260618/cloudridge_5m_qfq_service_confirmed_20080101_20260615_levels.csv`
2. `output/filter-parameter-workflow/cloudridge_20260521/service_confirmed_qfq_levels/cloudridge_1d_qfq_service_confirmed_20080101_20260519_levels.csv`

5m 数据源会按 `trading_day` 取最后一根 K 线聚合成日线。这样当前基础设施保持日线统一口径，同时能消费更新的数据源。

## 属性面与解释边界

当前 V1 覆盖以下属性族：

| 属性族 | 列模式 | 解释 |
|---|---|---|
| BDCI | `bdci_w{window}` | 方向连续度：短窗看最近方向切换是否减少，长窗看底层是否长期单向化；它不看幅度，必须和 WBI/DII/波动合读。 |
| BCI | `bci_upshare_w{window}`, `bci_downshare_w{window}`, `bci_imbalance_w{window}` | K 线颜色比例：短窗看最近上涨/下跌日数量投票，长窗看长期颜色偏斜和潜在获利盘；它不看幅度。 |
| WBI | `wbi_w{window}` | 幅度加权方向压力：短窗看局部卖压/买压是否有真实幅度，长窗看大背景方向压力；长强短弱常用于观察局部流动性先断裂。 |
| PWBCI | `pwbci_score_w{window}`, `pwbci_path_rank_w{window}`, `pwbci_imbalance_w{window}` | 路径强度加权颜色偏斜：判断颜色偏斜是否带有路径能量；更适合趋势许可或反卖出保护候选。 |
| DII | `dii_score_w{window}`, `dii_impulse_w{window}`, `dii_efficiency_w{window}`, `dii_energy_w{window}` | 方向冲量：合成净位移、路径能量和效率；解释力强但可能偏同步，不能跳过事件前验证。 |
| JRR | `jrr_score_w{window}`, `jrr_reversal_rate_w{window}`, `jrr_volatility_rank_w{window}`, `jrr_vol_of_vol_rank_w{window}` | 跳变反转风险：描述强 K 线后无缓冲反向、滤波失效和暴跌后反弹环境；含波动秩，不能包装成独立领先因子。 |
| Lag memory | `lag1_autocorr_w{window}`, `lag4_autocorr_w{window}` | 收益记忆性：`lag1` 看隔日延续/反向修复，`lag4` 看周节奏承接；长窗 `lag4` 偏低常表示周内方向性缺失。 |
| Volatility | `volatility_w{window}`, `vol_of_vol_w{window}`, `mean_abs_return_w{window}` | 波动和活跃度：短窗常偏同步，长窗可描述市场弹性、控盘钝化或冲击放大环境；它不是方向。 |
| Path shape | `path_efficiency_w{window}` | 路径单边效率：回答“走得直不直”，不回答“向上还是向下”；必须和 WBI/DII 或 BCI 合读。 |
| Paper EWMA kernel return | `paper_kernel_daily_gross_return_s{span}` | 论文原式欧式趋势系统的逐日实现毛收益核；固定16个尺度（1、2、3、4、5、10、15、20、30、60、100、150、200、300、400、500日），严格滞后一日，不设第二估计窗、不输出路由。 |

默认通用属性窗口为 `20/50/100/200/300/400/500` 个交易日。默认均线窗口同样为 `20/50/100/200/300/400/500`。论文EWMA核独立使用 `1/2/3/4/5/10/15/20/30/60/100/150/200/300/400/500` 十六个信号尺度，只在整条历史起点预热250日，不存在250日滚动测量尺，也不再自动堆叠通用MA面。该属性只能从[唯一渐进式入口](../user/cloudridge_paper_kernel_multiscale_timeseries_workflow.md)进入，不得绕过入口直接把白皮书或历史证据当成机器权威。

解释深度按证据强弱分层：BCI、WBI、lag memory、path shape 可较具体地解释市场结构；DII、JRR 和 volatility 因为更容易混入同步状态，字典中保留更强的使用边界。后续策略不得为了追求叙事完整而把弱解释属性强行写成因果门控。

## 风险策略关系

Residual Risk-Off 近期研究已经证明一个重要治理要求：不能把“暴跌样本的属性值分布集中在历史常见区域”误判为门控规律。属性基础设施只产出值，不产出分位区间结论。后续风险策略必须围绕三段流程开发：

1. 命中：低通频段先决定是否进入大级别下跌候选。
2. 风险预测点：在候选事件前寻找可见的开门/打分/触发状态。
3. 风险停止点：研究暴跌后反弹和风险解除，防止长时间误覆盖。

属性基础设施服务第 2、3 步，但不替代第 1 步的事件锚，也不替代最终回测。

## 重建与验收

重建：

```bash
PYTHONPATH=src uv run python scripts/build_cloudridge_attribute_infrastructure.py
```

最小验收：

```bash
PYTHONPATH=src uv run pytest tests/unit/test_cloudridge_attribute_infrastructure.py -q
```

文档一致性验收：

```bash
PYTHONPATH=src uv run pytest tests/unit/test_documentation_consistency.py -q
```

验收通过后，后续 AI 从 `ai-readme.md` 或 `docs/00-index.md` 能一路找到本白皮书、用户文档、代码入口、构建脚本和当前权威产物目录。
