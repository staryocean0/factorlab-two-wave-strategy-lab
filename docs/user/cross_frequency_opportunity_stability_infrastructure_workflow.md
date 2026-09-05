# 跨频收益机会与稳定性潜力 V2 工作流

渐进式入口：[当前注册表](../ops/cross_frequency_opportunity_stability_registry@2.0.json) → [版本链](../ops/cross_frequency_opportunity_stability_version_registry@1.0.json) → [白皮书](../ops/cross_frequency_opportunity_stability_infrastructure_whitepaper.md) → [核心代码](../../src/factor_lab/market_state/cross_frequency_opportunity_infrastructure.py) → [测试](../../tests/unit/test_cross_frequency_opportunity_infrastructure.py) → [V2证据](../ops/evidence/csi1000_cross_frequency_opportunity_stability_v2_20260828/)。

## 一键构建

在 FactorLab 根目录执行：

```bash
PYTHONPATH=src python scripts/build_csi1000_cross_frequency_opportunity_stability_v2.py
```

构建器读取2014热身、2015–2020开发材料、2022–2024重复审计和已冻结MO事件；它会解析ASK-BID端点，但不会计算任何策略收益。

## 一键验证

```bash
PYTHONPATH=src pytest -q tests/unit/test_cross_frequency_opportunity_infrastructure.py
ruff check \
  src/factor_lab/market_state/cross_frequency_opportunity_infrastructure.py \
  scripts/build_csi1000_cross_frequency_opportunity_stability_v1.py \
  scripts/build_csi1000_cross_frequency_opportunity_stability_v2.py \
  scripts/validate_csi1000_cross_frequency_opportunity_stability_v1.py \
  scripts/validate_csi1000_cross_frequency_opportunity_stability_v2.py \
  tests/unit/test_cross_frequency_opportunity_infrastructure.py
basedpyright \
  src/factor_lab/market_state/cross_frequency_opportunity_infrastructure.py \
  scripts/build_csi1000_cross_frequency_opportunity_stability_v1.py \
  scripts/build_csi1000_cross_frequency_opportunity_stability_v2.py \
  scripts/validate_csi1000_cross_frequency_opportunity_stability_v1.py \
  scripts/validate_csi1000_cross_frequency_opportunity_stability_v2.py
PYTHONPATH=src python scripts/validate_csi1000_cross_frequency_opportunity_stability_v2.py
```

正式验收还必须物化隔离树并冻结逐文件摘要：

```bash
replay_dir=$(mktemp -d "$PWD/.tmp/crossfreq-v2-replay-XXXXXX")
PYTHONPATH=src python scripts/build_csi1000_cross_frequency_opportunity_stability_v2.py \
  --output "$replay_dir/results" \
  --registry "$replay_dir/registry.json"
PYTHONPATH=src python \
  scripts/validate_csi1000_cross_frequency_opportunity_stability_determinism_v2.py \
  --isolated-root "$replay_dir/results"
PYTHONPATH=src python scripts/validate_csi1000_cross_frequency_opportunity_stability_v2.py
```

验证器会独立重算机会总量与7bp恒等式，检查段间状态重置、暖机不进入机会、25×25矩阵、225个自然年单元、400个12月/6月边界视图、端到端执行漏斗、精确小周期Rademacher敏感性、四offset边界图、依赖修正、Pareto无总分以及源码/输入/运行时/产物摘要闭包。

## 读结果的顺序

1. `answerability_report.json`：先确认只允许回答机会潜力和稳定性潜力。
2. `frequency_platform_dependency.csv`：确认哪些相邻P值属于同一有效研究平台。
3. `return_opportunity_potential_pareto.csv`：看收益机会潜力的非支配平台。
4. `stability_potential_pareto.csv`：看稳定性潜力的非支配平台；不要把它称为 Sharpe。
5. `period_potential_summary.csv`：查看每个P值各轴原始值。
6. `execution_feasibility.csv`：同时检查全episode→上游resolved→条件L1→端到端L1漏斗、延迟、点差和容量；这里没有策略收益。
7. `annual_and_12m_step6m_stability.csv`：自然年才是独立票，滚动窗口只看边界敏感。
8. `rademacher_null_sensitivity.csv`：检查条件高斯近似对P16/P24精确随机符号期望的偏差。
9. `opportunity_cost_sensitivity_surface.csv`、`frequency_curve_shape.csv`、`opportunity_offset_sensitivity_surface.csv`和`offset_peak_stability.csv`：同时检查成本和offset边界；不得把指数bp与期权权利金bp直接等同。
10. `counterexample_ledger.csv`：逐条检查优先平台为何仍不能升级为收益或生产结论。

## 结果字段的正确叫法

- `annualized_*_opportunity_pct`：原始事后方向容量天花板，只作次级参考。
- `annualized_excess_*_opportunity_pct`：减去同等实现方差的条件高斯折叠正态近似后的超额机会；不是精确Rademacher，也不是策略年化收益。
- `natural_year_*_floor`：机会下限，不是最大回撤保护。
- `pareto_nondominated=true`：没有被其他平台在所有注册轴上全面压过，不是第一名。
- `conditional_both_endpoint_exact_l1_coverage`：只是上游resolved子集中的二次覆盖。`end_to_end_both_endpoint_exact_l1_coverage`才使用全部预期episode分母，Pareto只使用后者。
- `scalar_score`：必须为空。

## 扩展新的频段或载体

新增周期时，必须先更新预注册和坐标表，然后同时补齐属性、机会、执行、依赖、自然年、滚动窗口和反例。不能只增加一条收益曲线。

新增期货期权或ETF期权载体时，手续费在用户绑定前必须保持 `unbound`；ASK-BID价格仍只允许入场ASK、出场BID和一个显式手续费，不能重复扣除时间价值、代理点差或额外冲击。

## 何时可以进入策略研究

只有用户明确授权某个研究平台进入策略开发后，才启动新的 `$strategy-slice-rebuild`：年度切片产生材料，失败策略整体重建，默认补12个月/6个月压力图谱，并保留真正未见时期。当前跨频结果已经消费2015–2020和2022–2024，不能再把这些年份称为新鲜 OOS。
