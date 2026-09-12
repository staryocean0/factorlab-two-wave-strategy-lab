# 衍生品测量/执行池历史工作流

> 当前测量权威已迁入Layer 1/2。新入口见
> [期权波动率L1/L2–Layer4工作流](timing_option_volatility_l1_l2_layer4_workflow.md)。

本页是第 5 池高阶字段的操作入口。目录级身份仍走
[属性池更新工作流](market_state_attribute_pool_update_workflow.md)。
合同见[白皮书](../ops/market_state_derivatives_execution_pool_whitepaper.md)。

## 日频 IV / Greeks（现属Layer 2）

```bash
PYTHONPATH=src .venv/bin/python \
  scripts/materialize_market_state_derivatives_execution_pool_v1.py
```

读取 DataHub 中金所日频结算、固定合约身份、固定 3M/6M/1Y 曲线和
`lat_cffex_underlyings_20260823` 指数日线，写出 moneyness 参考表、折现 Black-76
IV/Greeks（含固定远期 Rho）和 ATM/25Δ/期限摘要，并写固定 3 秒产品的身份回执。

证据写入
`docs/ops/evidence/market_state_derivatives_execution_pool_v1_3_20260826/`。
不要回写 2026-08-24 的 V1 freeze。

## 3 秒成交活跃度

本池不复制 3 秒明细，只固定 v4、consumer contract 和 manifest hash。V2 registration envelope 与 exact serving 链验证通过后标记 ready。刷新就绪矩阵（不重算 Black-76）：

```bash
PYTHONPATH=src .venv/bin/python \
  scripts/materialize_market_state_derivatives_execution_pool_v1.py \
    --refresh-readiness-only
```

```bash
.venv/bin/python scripts/update_market_state_attribute_pool_infrastructure.py --publish
.venv/bin/python scripts/update_market_state_attribute_pool_infrastructure.py --validate-current
```

## 验收

```bash
.venv/bin/pytest -q \
  tests/unit/test_cffex_index_option_black76.py \
  tests/unit/test_derivatives_execution_pool.py
```

看 `execution_capability_readiness.parquet`，不要只看脚本退出码。市场冲击必须保持
blocked。IV/Greeks/Rho 的全历史 `ok_ratio` 低于 0.80 只能标 partial；Rho 必须明确
`forward held constant`，不得解释成总利率暴露。

## 禁止

- 把 CloudRidge ATM 代理写成认证 IV；
- 把 3 秒成交桶写成逐笔、主动方向、连续 L1 或冲击成本；
- 在 FactorLab 复制 3 秒全量明细或重新物化已退役高频源/1m；
- 用本池字段给策略或生产授权；
- 在本基础设施任务里开始 LAT 中证 1000 期权变体。
