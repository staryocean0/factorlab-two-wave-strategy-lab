# 六轴与工具专属因子统一基础设施白皮书

> 四层拆分：`six_axis_common_market_state` 是 Layer 2 测量；
> `tool_relative_coupling` 是 Layer 3a 工具基础。现有公式原地复用，未搬迁。

> 版本：1.0（2026-08-07）
>
> 阶段：统一基础设施交付（目录 + 耦合 + 完整性对账），不是因子有效性研究
>
> 权限：`measurement_authority=true`；信号/路由/动态参数/生产权限全部为 `false`

## 1. 设计决策

选择"保留子系统权威 + 新增统一目录/物化/查询编排层"，并将公共市场状态、工具相对耦合量与执行约束作为三个独立层。

### 驱动因素

1. 旧六轴和 R2F 已有大量冻结证据与失败记录，不宜改写。
2. 六轴标题不是每个工具的充分统计量，工具公式需要专属匹配量。
3. 下游需要一个入口，但单体实现会制造复制、漂移和不可验证性。

### 拒绝的备选方案

1. **把 13/14 工具专属因子全部并入 `timing_six_axis.py`**：拒绝。会混淆公共市场事实与工具相对量，使六轴失去策略中立性。
2. **只在文档中做索引**：拒绝。无法机器对账、物化时序、验证缺口或支持统一查询。
3. **直接建一个新的巨型因子表并全量入模**：拒绝。会重复同根因子并扩大多重检验/过拟合风险。

### 后果

- 对用户只有一个公开查询和构建入口；
- 对实现仍保持模块化和原权威单一来源；
- 不同工具可消费不同因子子集；
- 新增因子物化不会自动变成动态参数规则。

## 2. 三层因子模型

### 2.1 公共市场状态层（common_market_state）

收编六轴标题与已有多尺度分量。**标题只是简单监控投影**，不是调参的充分统计量；下游研究应读多尺度分量与期限结构。

截面轴缺失时保持缺失，不用云脊自身填充（`docs/user/market_state_timing_six_axis_workflow.md:56`）。

### 2.2 工具相对耦合层（tool_relative_coupling）

由工具真实公式倒推，将公共状态与工具内部决策量联系，优先无量纲比值：

- 群延迟 / 同向段年龄；
- 决策边际 / 局部噪声；
- 轨宽响应缺口；
- 均值间距 / 噪声；
- 频带内能量 / 带外噪声等。

复用已有 11 机制、34 因子（21 已有 + 13 缺失）、43 映射边。**映射边不是独立因子，43 边不是 43 票**。

### 2.3 执行约束层（execution_constraint）

成本、执行延迟、最短持有、载体频率、T+1/下一棒执行等约束。

## 3. 因子权限梯度（必须分离）

| 梯度 | 含义 | 本轮默认 |
| --- | --- | --- |
| `defined` | 公式与语义完整 | — |
| `materializable` | 输入齐全、可严格因果生成 | 目录构建时的候选状态 |
| `materialized` | 时序与质量回执存在 | 当前日线载体已生成 12 个候选量 |
| `research_supported/rejected/unknown` | 实证地位 | 全部 `research_unknown` |
| `routing/parameter/production_authorized` | 独立权限 | 全部 `false` |

**禁止从 `defined` 或 `materialized` 跳级到"有效"。** 物化成功不得自动宣称因子有效；局部工具对证据不得冒充跨工具普遍规律（`docs/ops/market_state_tool_formula_mechanism_whitepaper.md:258-283`）。

物化回执必须绑定真实载体。当前包只物化 `1d`；`60m/15m` 只有另行实现并生成独立质量回执后才能登记为已物化。每个时序因子保留首个/末个有效决策时点；预热期保持 `NaN`，短历史导致全空列时整个构建失败，禁止用 `0/-0` 或全空列伪造可用性。

研究前提门的失败同样不得被压成一个布尔值。统一基础设施调用2.1恢复合同，区分“补材料”、“换方向”和“判死已声明对象”，新一轮以父子run谱系继续，不允许在旧失败run中回写规则。

## 4. 第 14 工具 append-only 扩展

`paper_kernel_multiscale_trend_router` 的公式从策略原型因果倒推：

- 12 尺度归一化收益 EWMA 核（spans ∈ {5,10,15,20,30,60,100,150,200,300,400,500} 天）；
- 慢/中/快层级路由：`down=slow<=-boundary and middle<0`；`up=slow>=boundary and middle>0`；否则 flat；
- macro_up/flat 应用 fast_direction_hysteresis；macro_down 仅允许单独武装的快速反弹。

参数信号相关性审计（F1 规则，`docs/user/market_state_tool_formula_mechanism_workflow.md:45-54`）：

| 参数 | 信号相关性 | 说明 |
| --- | --- | --- |
| `macro_boundary` | direct | 改变宏观 regime 切换阈值 |
| `fast_hysteresis` | direct | 改变快速方向路由滞回带 |
| `rebound_oversold_strength` | direct | 改变反弹武装门槛 |
| `rebound_entry_score` | direct | 改变反弹入场门槛 |
| `rebound_failure_score` | direct | 改变反弹退出门槛 |
| `bars_per_day` | direct | 直接乘进每条 EWMA 信号线 `span_bars`（`nu=1-2/(span_bars+1)`）与波动率归一化周期，改变信号（已实证不同取值在数千根 K 线上决策分歧） |
| `cost_bps` | cost_only | 改变成本项，不改买卖序列 |

只有 `direct` 参数进入当前信号调参候选；`cost_only` 不进入当前信号调参自由度。该工具**未伪造历史 R2 验证结论**；旧 13 工具前缀字节不变。

## 5. 拓扑与同根压票

拓扑必须显式区分四种关系，**禁止用相关阈值冒充正交性**：

- `exact_alias`：`path_efficiency_wN == abs(direction_wbi_wN)`，`noise_ratio_wN == 1 - path_efficiency_wN`；
- `same_root_projection`：ACF / variance_ratio / 论文核投影 / Hurst / BDCI 同根（`docs/user/market_state_timing_six_axis_workflow.md:54`）；
- `conditional_orthogonal`：仅在所述条件下正交；
- `unknown_relation`：关系未刻画。

同根代理归入同一 `proxy_family_id`，可互证，**禁止当成多个独立因子重复投票**。多重检验校正单位是 11 个机制家族，不是 43 条边。

## 6. 负面研究证据的继承

本基础设施不重跑、不绕开以下已冻结负结果：

- 单因子层：34 因子中 31 个在某具体工具对通过，但 **0 个跨工具普遍支持**；11 机制中 10 个有局部信号，**0 个通过年度时间块 + 11 家族多重检验**（机制 10 均值尺度分离连局部门都失败）。
- 44 个工具对总公式通过外层折，仅作为具体工具对候选，不能证明任何因子/机制有全市场路由权。
- A-E 参数规律发现：在 `{六轴 6 + rolling_acf_length + rolling_hurst} × {SMA-down + bandpass} × {scaling-law + 7 公式族} × 2009-2017` 上**无可信择时参数规律**；`τ=rolling_dominant_period` 因物理前提不成立已移除。

不重跑公式、条件、工具对、数据身份全部相同的旧否决实验。因子新增尺度、公式或工具对变化时，先生成新身份与变更理由。

## 7. 五位一体产物

| 类型 | 位置 |
| --- | --- |
| 文档 | `docs/user/market_state_unified_timing_factor_infrastructure_workflow.md` |
| 白皮书 | 本文件 |
| 代码 | `src/factor_lab/market_state/timing_factor_catalog.py`、`tool_factor_coupling.py`、`unified_timing_infrastructure.py` |
| Schema | `market_state_timing_factor_catalog@1.0`、`market_state_tool_factor_coupling@1.0`、`market_state_unified_timing_infrastructure_manifest@1.0` |
| 测试 | `tests/unit/test_market_state_unified_timing_infrastructure.py` |
| 工作流 | build / validate / query 三入口（见工作流文档） |

五位一体不是写五段文字，而是**文档命令、白皮书契约、代码入口、测试断言与工作流产物相互对账**。

## 8. 下一道门

13 个缺失因子均保持 `proposed`：其中 12 个已在日线载体严格因果物化，1 个因缺少 `directional_run_age` 上游输入保持 `blocked_missing_input`；证据状态仍全部为 `research_unknown`。只有完成同根代理去重，并在 2009—2020 冻结时间外方案中解释参数/工具相对损失差，才可进入第二代 R2。自本版起，“解释相对损失差”还必须满足：先从载体已使用趋势输入中残差化，再证明预注册极端状态对应策略绝对大亏损或相对持有大幅跑输；静态基线必须在开发期前冻结，不能用全样本事后最优冒充基准。当前没有任何新状态、信号、动态参数、工具路由或生产权限获得授权。

自本版起，完整性门之后的所有动态参数和工具路由实证，统一进入
[`market_state_timing_strategy_prerequisite_workflow.md`](../user/market_state_timing_strategy_prerequisite_workflow.md)。
该工作流保留九个可分别证伪的命题，但不再把它们强制串成九个硬门。
身份时钟、可控性、可识别性、在线相对信息和时间可用性构成硬前提；
机制归因与属性补全是S2后的并联非阻断支线；未解释或高容量候选在样本外层承担更强证据义务。
四类策略适配器继续保留各自的原生公式、属性和规则形态。
