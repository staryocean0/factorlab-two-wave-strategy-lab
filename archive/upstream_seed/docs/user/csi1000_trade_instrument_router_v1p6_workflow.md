# 中证1000股指期权交易工具路由器 V1.6 工作流

## 输入职责

上游策略或预测 AI 只提交方向、联合退出情景和退出规则身份。它不得提交合约代码、行权价、档位、DTE 或 IV 阈值。

执行/风险层提交选择目标、张数、预算、深度、到期和下尾约束。V1.6 从固定 MO/IM/利率/BBO 链取得完整候选市场状态。

## 最小中性情景示例

```json
{
  "contract_id": "JointScenarioMORoutingRequest@1.0",
  "request_id": "request-001",
  "trade_id": "trade-001",
  "strategy_id": "strategy-x",
  "strategy_version": "v1",
  "forecast_id": "forecast-001",
  "provider_id": "provider-x",
  "provider_version": "1.0",
  "scenario_assembly_id": "neutral-iv-three-state-v1",
  "exit_policy_id": "fixed-upstream-exit-v1",
  "exit_policy_version": "1.0",
  "generated_at": "2026-09-01T09:59:59+08:00",
  "route_time": "2026-09-01T10:00:00+08:00",
  "valid_until": "2026-09-01T14:00:00+08:00",
  "direction": 1,
  "scenarios": [
    {
      "contract_id": "JointMOExitScenario@1.0",
      "scenario_id": "adverse",
      "probability": 0.20,
      "exit_seconds": 900,
      "directional_return_bp": -100,
      "iv_level_shift": 0.00,
      "iv_term_slope_shift_per_year": 0.00,
      "iv_skew_shift_per_log_moneyness": 0.00,
      "iv_curvature_shift_per_log_moneyness_sq": 0.00,
      "exit_spread_multiplier": 1.00
    },
    {
      "contract_id": "JointMOExitScenario@1.0",
      "scenario_id": "base",
      "probability": 0.55,
      "exit_seconds": 3600,
      "directional_return_bp": 80,
      "iv_level_shift": 0.00,
      "iv_term_slope_shift_per_year": 0.00,
      "iv_skew_shift_per_log_moneyness": 0.00,
      "iv_curvature_shift_per_log_moneyness_sq": 0.00,
      "exit_spread_multiplier": 1.00
    },
    {
      "contract_id": "JointMOExitScenario@1.0",
      "scenario_id": "tail",
      "probability": 0.25,
      "exit_seconds": 7200,
      "directional_return_bp": 260,
      "iv_level_shift": 0.00,
      "iv_term_slope_shift_per_year": 0.00,
      "iv_skew_shift_per_log_moneyness": 0.00,
      "iv_curvature_shift_per_log_moneyness_sq": 0.00,
      "exit_spread_multiplier": 1.00
    }
  ],
  "support_count": 100,
  "forecast_status": "ready_joint_scenarios",
  "source_material_digest": "<64-char-sha256>",
  "research_only": true
}
```

中性情景只表示尚无 IV/流动性预测。若有外部预测，应在同一概率情景中填入 IV 水平、期限、偏度、曲率变化和退出价差倍数，不得把彼此无关的边际均值强行拼接。

## 风险委托示例

```json
{
  "contract_id": "JointScenarioMOSelectionMandate@1.0",
  "requested_contracts": 1,
  "maximum_visible_l1_participation": 0.5,
  "minimum_expiry_buffer_seconds": 14400,
  "maximum_premium_cash_rmb": 50000,
  "objective_id": "max_expected_net_return_on_premium",
  "minimum_expected_net_pnl_rmb": 0,
  "minimum_probability_positive": 0.50,
  "cvar_alpha": 0.10,
  "maximum_cvar_loss_return": 0.50,
  "iv_term_reference_seconds": 2592000,
  "exercise_or_assignment_allowed": false
}
```

## 调用顺序

1. 校验请求身份、SHA256、因果时钟、退出规则和概率和；
2. 历史研究优先通过`joint_scenario_candidates_from_continuous_bbo_chain(...)`取得连续BBO、重新反演IV并保留完整挂牌分母；`joint_scenario_candidates_from_datahub_chain(...)`旧3秒入口只作兼容，不与连续BBO拼接。日内曲面位移必须在 route/exit 共同的唯一 `contract_symbol` 支持上测量，并另行保留完整分母的拒绝状态账本；
3. 构建每张合约的逐情景退出结果；
4. 聚合期望、概率、分位数和 CVaR；
5. 应用执行/风险约束；
6. 按显式目标确定性排序；
7. 输出研究级最优 MO 或 `NO_TRADE`，保留全部候选卡摘要；
8. 合约一旦选择，在上游退出规则完成前冻结，不允许途中按事后赢家换券。

## 构建与验证

```bash
PYTHONPATH=src python scripts/build_csi1000_trade_instrument_router_v1p6.py --overwrite
PYTHONPATH=src python scripts/validate_csi1000_trade_instrument_router_v1p6.py
PYTHONPATH=src python scripts/materialize_csi1000_router_v1p6_round2_bounded_sample.py --verify-existing
PYTHONPATH=src pytest -q \
  tests/unit/test_csi1000_joint_scenario_option_matcher.py \
  tests/unit/test_csi1000_holding_aware_option_matcher.py \
  tests/unit/test_csi1000_expectation_carrier_matcher.py \
  tests/unit/test_csi1000_trade_instrument_router.py

PYTHONPATH=src pytest -q \
  tests/unit/test_csi1000_mo_continuous_bbo_research.py \
  tests/unit/test_csi1000_joint_exit_scenario_provider_contract.py \
  tests/unit/test_csi1000_mo_intraday_iv_surface_measurement.py \
  tests/unit/test_csi1000_mo_intraday_iv_panel.py \
  tests/unit/test_csi1000_mo_exit_spread_provider.py
```

## 停止规则

- 不读取策略实现收益验证通用 V1.6；
- 不从合成测试宣称某个档位、DTE、IV 状态或目标函数经济最优；
- 不把路径字段直接加进期权价格；
- 不把中性 IV 假设命名为 IV 预测；
- 不授予真实路由或生产权限。
- G2A/G2B-P任一没有临时预测头时，不启动G1科学组装；G1不通过时，不读G3经济结果。
- 不用锁箱、一次性挑战或G4数据挽救开发头。
