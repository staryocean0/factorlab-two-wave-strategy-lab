# 中证1000股指期权交易工具路由器 V1.6 白皮书

状态：联合情景研究基础设施闭合；无历史经济优胜结论、无真实路由权、无 fresh OOS、无生产权。

## 1. 基础设施定位

V1.6 是策略无关的 MO 合约选择底座：

```text
上游策略/预测AI
  -> 方向 + 概率加权联合退出情景 + 退出规则身份
执行/风险层
  -> 目标函数 + 风险约束 + 资金/容量约束
V1.6
  -> 完整MO候选情景卡
  -> 声明模型与委托下的最优MO或NO_TRADE
```

它不从期权 IV、偏度、价差或盘口反向制造方向 Alpha，不自己预测未来收益、持仓时间、路径、IV 或流动性，也不读取任何策略的实现收益。

## 2. 为什么 V1.5 需要升级

V1.5 已经实现持仓感知、精确时间推进 Black-76、费用、当前价差、一档容量、完整候选分母和 `NO_TRADE`，但它的输入还是几个彼此分离的摘要：

- 同一组收益分位数只在期望持仓时点定价；
- 最短/最长持仓只改变 Theta，没有自己的收益状态；
- 方向正确概率没有进入期望值；
- IV 只有固定正负五个百分点敏感性；
- 最优目标固定为权利金收益率。

问题的根不是缺少另一个策略回测，而是缺少一个联合概率空间。期权退出价值至少同时依赖退出标的价格、退出时刻、剩余期限、退出 IV 和退出成本，这些量不能分别取均值后再拼接。

## 3. V1.6 输入 Protocol

### 3.1 上游必须提供

`JointScenarioMORoutingRequest@1.0` 包含：

- `direction`：+1 看多、-1 看空；
- 一组 `JointMOExitScenario@1.0`，概率严格和为一；
- 冻结的 `exit_policy_id/version`；
- provider、strategy、forecast、scenario assembly 和 source digest；
- `generated_at <= route_time <= valid_until`；
- support 和 `forecast_status=ready_joint_scenarios`。

每个联合情景包含：

- `probability`；
- `exit_seconds`；
- `directional_return_bp`：沿预测方向为正，方向错误为负；
- `iv_level_shift`；
- `iv_term_slope_shift_per_year`；
- `iv_skew_shift_per_log_moneyness`；
- `iv_curvature_shift_per_log_moneyness_sq`；
- `exit_spread_multiplier`。

因此方向正确概率等于方向收益为正的情景概率之和，不再是一个没有进入计算的旁路字段。

### 3.2 可选路径上下文

上游可以整组提供：

- 预期振幅；
- 路径效率；
- MFE；
- MAE；
- 到达 MFE 的时间。

这些字段只能解释上游如何形成退出情景，不能直接进入 Black-76。固定退出状态下，修改这些字段不会修改期权价格。若路径会触发止盈、止损或提前退出，上游必须先按冻结退出规则把作用转换为不同情景的 `exit_seconds` 和 `directional_return_bp`。

### 3.3 当前没有预测值时怎么办

接口允许显式的中性假设：

- IV 水平、期限、偏度、曲率变化填零；
- 退出价差倍数填一；
- 路径上下文整组省略。

但 provider 必须把这种输入标记为中性情景假设，不能冒充预测。冷启动、样本为零或非 `ready_joint_scenarios` 请求一律失败关闭。

## 4. 执行与风险委托

`JointScenarioMOSelectionMandate@1.0` 不由预测策略控制。它明示：

- 张数；
- 最大 Ask1 参与率；
- 到期缓冲；
- 最大权利金预算；
- CVaR 下尾概率；
- 最低期望净现金；
- 最低盈利概率；
- 最大允许 CVaR 损失。

目标必须在以下三者中显式选择：

1. `max_expected_net_return_on_premium`；
2. `max_expected_net_pnl_rmb`；
3. `max_probability_positive`。

同一批合约在不同目标下可能有不同最优项。例如权利金收益率会偏向高凸性，净现金目标在固定张数下更偏向高 Delta。V1.6 不把这种偏好伪装成市场普遍规律。

## 5. 联合情景定价

对合约 `j`、情景 `s`：

```text
F_exit = F_now × (1 + direction × directional_return_bp / 10000)
T_exit = (seconds_to_expiry - exit_seconds) / seconds_per_year
m      = log(K / F_exit)

IV_exit = IV_now
        + level_shift
        + term_shift × (T_exit - reference_term)
        + skew_shift × m
        + curvature_shift × m²
```

然后使用 Black-76 对 `F_exit/K/T_exit/IV_exit/rate` 重定价。买入使用当前 Ask1；退出 Bid 代理为模型公允价减去当前半价差乘情景退出价差倍数；每张扣除往返 28 元。

情景结果按概率聚合为：

- 期望净现金；
- 期望权利金净收益率；
- 净盈利概率；
- P10/P50/P90；
- 最差情景；
- 概率加权下尾 CVaR。

这是一套透明的条件情景计算，不是对未来期权价格的保证。

## 6. 候选与 `NO_TRADE`

`joint_scenario_candidates_from_datahub_chain(...)`把固定 DataHub MO/IM/利率链转换为 V1.6 候选。它以挂牌 MO 身份全集为分母：即使某张合约缺报价、缺 IV、缺期限或缺可见深度，也保留一个无效市场状态候选并生成拒绝卡，不允许调用者只把“算得出来的赢家”传入。

Round 2新增`joint_scenario_candidates_from_continuous_bbo_chain(...)`：它以固定连续quote-change BBO替换旧3秒成交后报价，并重新反演mid IV；同月IM远期、利率、到期身份和完整挂牌分母仍由固定链提供。连续BBO仅有历史回放、`receipt_exact_pit=false`且未注册serving；旧3秒适配器只保留兼容研究入口，二者禁止拼接成同一测量轴。当前共同支持截止2026-08-14，之后到2026-08-25的BBO尾段因缺当前IM 1m身份而失败关闭。

完整 MO 分母不会因报价缺失、方向不符或风险失败而丢行。每张候选保留拒绝原因。以下情况失败关闭：

- 上游情景未就绪；
- Call/Put 与方向不符；
- 候选或报价非因果；
- 退出时刻越过到期或缓冲；
- Ask1 深度不足；
- 权利金超过预算；
- 任一情景生成非正或超模型边界的 IV；
- 期望、盈利概率或 CVaR 不满足委托。

先应用全部约束，再按显式目标、期望净现金、盈利概率、CVaR、深度参与率和合约代码确定性排序。没有合格合约时输出 `NO_TRADE`。最终决策同时绑定forecast/provider、退出规则身份和完整联合情景digest，避免合约冻结后悄悄更换上游假设。

## 7. 已闭合与未闭合

已闭合：

- 策略无关联合情景输入；
- 概率真正进入期望值、盈利概率、分位数和 CVaR；
- 收益、持有时间、IV 曲面与退出价差保持联合；
- 三种显式目标和风险/预算约束；
- 完整候选、确定性排序和 `NO_TRADE`；
- DataHub完整挂牌分母适配和无效市场状态拒绝卡；
- 连续BBO历史as-of、完整分母候选桥和G2B-M退出价差测量；
- G0T墙钟`exit_seconds`结果前合同；
- G1联合Provider结果前预注册合同（仅合同，不是Provider通过）；
- 日内IV四系数测量公式、支持门、合成精确复原，以及连续BBO-mid单日单时距的受限真实物化；
- G2A 116个开发交易日的日内IV时序测量面板，以及A0/A1/A2因果开发门裁决；
- G2B-P 18.55万条合约状态、55.65万条S0/S1/S2因果预测与开发门裁决；
- 路径上下文与实际定价权限分离；
- 路由计算内核的纯合成测试与来源封闭；受限真实测量证据不予上升为经济有效性。

未闭合：

- G2A A1/A2与G2B-P S1/S2均未通过结果前开发门，两个临时预测头均为空；
- 联合情景Provider尚未训练或校准；除两头失败外，上游`UpstreamReturnTimeForecast` rows也尚未物化；
- 三种目标谁具有长期经济优势尚未验证；
- 没有未来追加的真正未见挑战；
- 无真实路由和生产权。

Round3只读取2025-09-01至2026-02-27的116个开发交易日；61日聚合锁箱、54日一次性挑战、G4未来行和策略收益均为0读取。因为G2A/G2B-P均无临时头，G1启动门强制关闭；G3随G1关闭，G4只等待自然未来追加。

## 8. 五位一体

- 文档：`docs/ops/csi1000_trade_instrument_router@1.6.json` 与执行计划；
- 白皮书：本文件；
- 代码：`src/factor_lab/market_state/csi1000_joint_scenario_option_matcher.py`；
- 测试：`tests/unit/test_csi1000_joint_scenario_option_matcher.py`；
- 工作流：`docs/user/csi1000_trade_instrument_router_v1p6_workflow.md`；
- 构建/验证：`scripts/build_csi1000_trade_instrument_router_v1p6.py` 与对应 validator；受限真实物化由`scripts/materialize_csi1000_router_v1p6_round2_bounded_sample.py`可哈希重放。

V1.5 保持可重放历史版本，V1.6 只通过新 schema 扩展，不原地削弱旧合同。
