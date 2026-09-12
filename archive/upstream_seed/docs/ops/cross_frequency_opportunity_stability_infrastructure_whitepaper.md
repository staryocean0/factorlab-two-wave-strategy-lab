# 跨频收益机会与稳定性潜力基础设施白皮书

版本：2.0  
状态：研究测量基础设施；不构成策略、回测或生产授权  
当前机器注册表：[`cross_frequency_opportunity_stability_registry@2.0.json`](cross_frequency_opportunity_stability_registry@2.0.json)  
版本链：[`cross_frequency_opportunity_stability_version_registry@1.0.json`](cross_frequency_opportunity_stability_version_registry@1.0.json)  
用户工作流：[`cross_frequency_opportunity_stability_infrastructure_workflow.md`](../user/cross_frequency_opportunity_stability_infrastructure_workflow.md)

## 1. 要回答的问题与不能偷换的问题

本基础设施回答两个“策略前”问题：

1. 从超高频到低频，哪些物理频段具备更强的**收益机会潜力**？
2. 哪些物理频段具备更强的**稳定性潜力**？

它不直接回答“哪个频段的策略收益最高”或“哪个频段的策略 Sharpe 最高”。预期收益和 Sharpe 都属于一条包含方向、持有、换手、载体、执行和资金分配的日期化策略 PnL；频段本身没有 PnL。本基础设施因此只输出两套非支配 Pareto 平台，不输出总分和单一冠军。

## 2. 五位一体交付

| 层 | 权威表面 | 作用 |
|---|---|---|
| 文档 | 本白皮书、机器注册表、证据清单 | 冻结术语、公式、数据边界和权限 |
| 白皮书 | 本文件 | 解释为什么机会天花板不是收益、稳定性潜力不是 Sharpe |
| 代码 | [`cross_frequency_opportunity_infrastructure.py`](../../src/factor_lab/market_state/cross_frequency_opportunity_infrastructure.py) | 实现十项跨频产品和双 Pareto 协议 |
| 测试 | [单元测试](../../tests/unit/test_cross_frequency_opportunity_infrastructure.py)、真实树验证器、摘要独立重算 | 验证段间重置、成本恒等式、精确小周期Rademacher、offset边界、端到端分母和权限关闭 |
| 工作流 | 用户工作流与构建/验证脚本 | 一键物化、验证、读取和扩展 |

## 3. 数据和时间边界

- 唯一市场父序列：CSI1000 `000852.SH` 官方1分钟视图，数据版本 `bars_cn_index_1m_raw_canonical_tdx_20260825_v1_20260825`。
- 2014-10-17 至 2014-12-31：只作因果滤波热身。
- 2015–2020：已消费开发材料。
- 2021：数据缺口，不读取、不跨越；2022开始时重置全部Butterworth、diff、rolling和暖机状态。
- 2022–2024：已消费重复审计，不是新鲜 OOS。
- 2025以后：不读取。
- 执行面只复用已冻结 LAT/IARR 事件的合约和决策端点，以相同合约、决策后第一条同步3秒 L1、最长等待120秒解析报价。它只测覆盖、延迟、点差和一档容量，不计算策略收益。

自然年是独立证据票。12个月、步长6个月的重叠窗口仅用于边界敏感性，不能重复计票。

## 4. 统一物理坐标

注册25个物理周期：P16/P24/P32/P48/P60/P64/P96/P128/P181/P256/P362/P512/P570/P645/P720/P735/P795/P840/P960/P1200/P1800/P1920/P2400/P3000/P3840，单位均为1分钟交易棒。其中19个来自已冻结的1分钟全频曲线；P60/P570/P645/P735/P795/P840分别是15分钟P4/P38/P43/P49/P53/P56的相同物理分钟锚点；P1920保留为连续性锚点。每个坐标明确拆开：

- 原始采样载体：1分钟；
- 信号跨度：P；
- 机会观察期：`ceil(P/2)`；
- 决策间隔：`ceil(P/2)`；
- 最短与最长持有：均为 `ceil(P/2)`；
- 头寸字母表：`{-1, 0, +1}`；
- 是否隔夜：允许；
- 执行载体：MO近ATM冻结事件，仅作代表性可行性。

频段标签 `ultra_high/high/medium/low` 只方便阅读，不具备路由权。

## 5. 十项基础设施产品

### 5.1 跨频坐标注册表

`cross_frequency_coordinate_registry.csv` 将采样、物理周期、观察期、持有期、成本压力和执行载体拆成独立列，防止把“P参数”“K线周期”“持有时间”混为一谈。

### 5.2 因果属性立方体

`cross_frequency_attribute_cube.parquet` 在同一原始父序列上，为每个交易日和每个物理周期物化：

- 几何边界名义不重叠的因果 Butterworth 频带功率与功率份额；实际频响有过渡重叠，且份额依赖当前网格，只作诊断，无跨网格比较或Pareto权限；
- 原始价格路径效率和有符号路径效率；
- 方差比；
- 滤波分量路径效率、BDCI、方向运行年龄和一周期位移；
- 所有更快频带相对目标频带的累计功率负担；
- 机会结果不进入因果属性立方体；它们只存在独立的事件账本，避免被误当作同时点预测标签。

滤波分量很光滑不等于原始市场可交易；因此分量连续性和原始价格路径效率始终是两列。

### 5.3 干扰负担矩阵

`frequency_interference_burden_matrix.csv` 包含全部 25×25 目标/干扰频段组合，而不是只看相邻频段。它报告相对功率、方向一致、方向反转、位移相关及累计快速负担。由于Butterworth响应重叠，该矩阵是当前网格内诊断，不进入Pareto。

### 5.4 相位传播图

`causal_phase_propagation_graph.csv` 的节点均由当时可得的因果分量构成，再在历史上测量源频段 `t` 与目标频段 `t+0…5个交易日` 的关系。最佳边按绝对 Spearman 最大、相同则较短领先选取。该图是历史机制诊断，不是实时预测规则。

### 5.5 机会天花板

`opportunity_event_ledger.parquet` 将每个已声明时间角色独立重启，按 P/2 切成主offset的非重叠事件；暖机和角色边界事件被禁止。对每个事件：

```text
gross_ceiling = abs(log_close_end - log_close_start)
stress_ceiling = max(gross_ceiling - 7bp, 0)
```

它等价于事后知道方向、可选择做多/做空/空仓、固定持有 P/2 的上界。7bp只是统一指数摩擦敏感性，不是MO的ASK-BID成本声明。该天花板使用未来信息，只能作分母。

`scale_opportunity_ceiling_atlas.csv` 分别报告开发期、重复审计期、合并期和自然年。它不称作预期收益。

原始事后天花板对纯噪声也会呈现“周期越短、年化机会越高”的机械效应。V2把下式明确定义为“条件高斯折叠正态近似”，不再称精确随机符号零假设。对事件内1分钟收益 `r_i` ：

```text
sigma = sqrt(sum(r_i^2))
null_gross = sigma * sqrt(2/pi)
null_net(c) = 2 * [sigma * phi(c/sigma) - c * Phi(-c/sigma)]
excess_net = max(abs(sum(r_i))-c, 0) - null_net(c)
```

该公式仅在条件高斯语义下是解析期望；真正的Rademacher随机符号和取决于全部实现振幅。V2对P16/P24全体事件枚举精确符号组合，将误差物化到 `rademacher_null_sensitivity.csv`，并把最大单增量/条件sigma集中度进入不确定性。`excess_net`允许为负，不得再按事件截成零。

### 5.6 执行可行性立方体

`cross_frequency_execution_feasibility_cube.csv` 先报告完整漏斗：全部预期episode → 上游合约/端点解析 → 条件双端L1 → 端到端双端L1。后两个覆盖率必须分列，Pareto只允许使用端到端分母。它还测量：

- 入场和出场均解析到精确同步 L1 的比例；
- 平均及P95报价可得延迟；
- 入场/出场报价点差；
- 往返两端最小一档合约容量；
- 持有墙钟时间；
- 报价等待相对机会观察期的比例。

密集物理锚点中，P60→P64、P570→P512、P645→P720、P735→P720、P795→P840、P1920→P1800仅用于代表性执行可行性，最大尺度误差11.63%，标记 `nearest_within_12pct`。其余冻结周期精确绑定。120秒门使用真正的 `quote_available_at=bucket_end`，不再使用bucket start。执行立方体禁止任何含 `return`、`pnl`、`sharpe` 的输入列。

### 5.7 依赖与有效样本

`frequency_dependency_effective_sample_matrix.csv` 使用每日毛机会的两两 Spearman。相邻频段相关不低于0.75时合并为一个平台；只允许相邻节点连边，避免不连续频段被偶然相关强行拼接。

时间有效样本采用：

```text
N_eff = clip(N * (1-rho1)/(1+rho1), 1, N)
```

全频有效尺度数采用相关矩阵特征值参与率：

```text
K_eff = (sum(lambda))^2 / sum(lambda^2)
```

### 5.8 双 Pareto 协议

收益机会潜力最大化：条件高斯近似且经7bp压力后的年化超额机会、超额事件中位厚度、高斯归一路径效率和端到端精确L1覆盖；最小化offset、零假设近似、时期漂移与物理锚点误差。Butterworth功率份额和快速负担不再进入Pareto。

稳定性潜力最大化：自然年超额机会下限、12个月超额窗口下限、有效事件数、代表性报价覆盖；最小化自然年超额变异系数、头部5%绝对超额集中度和执行覆盖不稳定。

任何平台只有在所有轴有限时才可进入 Pareto 判断。输出是多个不被其他平台全面支配的研究平台；没有权重、总分或冠军。

### 5.9 成本敏感性与曲线形状

`opportunity_cost_sensitivity_surface.csv` 在0/1/2/3/5/7/10/15/20/30/50/75/100/150/200/300bp统一指数往返摩擦下，对每个物理周期重算条件噪声调整的超额机会。`frequency_curve_shape.csv` 逐成本报告相邻上升/下降数、斜率变号、是否单调、峰值周期以及开发/重复审计峰位是否一致。这些峰值仍是事后机会峰值，不是策略参数或生产路由。

V2另以0/1/4/1/2/3/4周期位移的四个固定offset构建 `opportunity_offset_sensitivity_surface.csv`和 `offset_peak_stability.csv`。它们只是相关边界视图，不独立投票。只有四个offset峰位完全一致才报告点峰，否则只报告频段走廊。单调判断使用 `max(1个年化百分点, 峰值的1%)` 经济容差。

统一指数收益单位与MO期权权利金报价点差bp不可直接换算；后者还受delta、gamma、合约与到期结构影响。成本曲线只用于回答“如果对所有频段施加同单位摩擦，峰值如何移动”。

### 5.10 源、运行时与确定性闭包

V2 manifest绑定核心模块、直接Butterworth实现、builder/validator/wrapper、测试、白皮书、工作流、四层索引、机器schema、预注册、审查发现、市场输入/回执、MO episode漏斗、报价manifest/分区和Python/NumPy/Pandas/SciPy/DuckDB/PyArrow/Jsonschema版本。验证器独立核对市场SHA、行数、起止时间、漏斗分母、quote可得延迟和所有artifact摘要。正式/隔离双树必须对科学文件逐字节比较。

## 6. 反例制度

每个优先平台必须同时携带“为什么不能升级成收益结论”的反例。当前反例还绑定已验收的1分钟与15分钟归因：

- 一分钟P128全体理想毛边际为正，不等于可执行子集有方向边际；
- 一分钟自相关和符号持续更高，但仍不赚钱，证明它们不能单独作为趋势盈利因子；
- 15分钟P38/P43/P53六年全部为正，是“市场没有趋势”的反例；
- ASK-BID运输可以抹掉薄边际，但不能反推低频现金指数策略也会遭受相同运输损失。

## 7. 权限与结论边界

本基础设施允许：测量、归因、构建机会/稳定性 Pareto、提出下一轮研究优先平台。

本基础设施禁止：生成交易方向、仓位、参数、策略回测、预期收益、真实 Sharpe、生产路由或部署。

如果需要回答真实收益或真实 Sharpe，下一步必须另行冻结完整策略，按年度顺序重建，并在未消费时期接受挑战；本轮结果不能充当那个挑战的 OOS。
