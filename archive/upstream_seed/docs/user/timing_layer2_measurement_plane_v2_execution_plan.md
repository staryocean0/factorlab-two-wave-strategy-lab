# Timing Layer 2 Measurement Plane V2 执行计划

状态：`execution_completed_2026-09-02`  
任务：`bd://fl-smqu6`  
范围：只优化四层架构中的第 2 层 K 线测量；第 3 层暂停  
权限：`strategy_selection=false`、`routing=false`、`production_authority=false`

## 1. 目标与最终形态

现有 Layer 2 已有 17 个资产和较强数学原件，但多数产品仍是年度 atlas、单载体
专题或研究包。V2 的目标不是再堆指标，也不是把 17 个实现搬进一个大目录，而是
建立一个统一、逐棒、严格因果、可按需计算、可被多策略复用的测量平面：

```text
Layer 1 DataHub bar receipt
  -> Layer2MeasurementCoordinate
  -> PIT core / volume / cross-sectional / lifecycle providers
  -> spectral phase-age / rolling carrier relationship providers
  -> future path distribution provider
  -> read-only consumer adapters
```

任何输出只允许是连续量、关系、频段、诊断、质量或不确定性。禁止输出认领、
动作、仓位、策略/频段选择或生产指针。

## 2. 继承与不改写

历史合同保持可查询，不原地弱化：

- `unified_kline_attribute_v3`：保留历史物化与年度 atlas；V2 后继只消费 Layer 1
  DataHub receipt，不再建立 FactorLab 墙钟 bar 工厂。
- `core_kline_attribute_v1`：56 列年度核心继续是冻结对账基线。
- `all_frequency_timing_v2_1`、`cross_frequency_opportunity_v2`：保留研究 atlas 和
  answerability 边界，不把 oracle/机会天花板变成运行时特征。
- 论文核 16 尺度、群体相关 20/60/120 日、六轴语义、BDCI 和端点通道公式原地
  保留；V2 通过 adapter 复用，不复制公式。
- `cloudridge_daily_attributes_legacy` 只保留兼容读取，不再作为新功能父级。

## 3. 数据与证据边界

本计划是基础设施升级，不是策略研究：

- 允许读取：源码、Schema、manifest、source registry、当前指针、测试、白皮书、
  已消费结论的摘要性需求描述。
- 禁止读取：用于候选排序的策略收益行、交易明细、lockbox 细节、未来标签、
  事后 winner 参数面。
- 任何未来属性训练必须另有明确训练前缀；同一行的 runtime feature future reads
  必须为 0。
- Layer 2 不裁决某个属性是否应该进入策略。策略消费必须另启
  `$strategy-slice-rebuild`。

## 4. 公共坐标合同

所有 Provider 必须使用 `Layer2MeasurementCoordinate@1.0`：

| 字段 | 含义 | 硬门 |
|---|---|---|
| `carrier_id` | Cloudridge、指数、行业、动态群体等载体身份 | 非空、不可静默改名 |
| `view_id` | Layer 1 注册的真实 bar 视图 | 必须绑定 receipt |
| `physical_horizon` | 物理时间/交易日尺度 | 禁止只写 bars 不写物理解释 |
| `observation_time` | 完整观测时点 | 有时区、严格递增 |
| `available_at` | 测量最早可见时点 | 不早于 observation_time |
| `source_id/version` | DataHub 或冻结研究载体身份 | 内容摘要必须可验证 |
| `estimator_id/version` | 数学估计器身份 | 语义变化必须升版 |
| `membership_version` | 群体/行业/主题成员版本 | 非群体可为空 |
| `gap_policy` | 缺口、午休、熔断、reset 处理 | 不允许静默填充 |
| `quality_status` | ready/partial/unavailable | 不得用缺失冒充 0 |

## 5. 阶段 A：公共根、能力矩阵与 current 对账

### 输入

- 四层冻结清单与 Lane 2 的 17 个资产；
- 当前 Layer 1 DataHub clock split；
- 属性池 base registry、current snapshot 和现有 V1/V2/V3 合同。

### 实现

1. 发布 `timing_layer2_measurement_plane@2.0` 机器合同和 Schema。
2. 实现 `Layer2MeasurementCoordinate`、`Layer2Capability`、注册表 validator。
3. 构建 17 资产能力矩阵，至少记录：粒度、载体、视图、期限、是否逐棒、是否
   PIT、是否可增量、已知缺口、后继阶段。
4. 对账 current pointer：实际 snapshot、source 数、文档声明与 registry 状态必须
   一致；漂移先记录 incident，不覆盖历史 snapshot。
5. 明确 Layer 4 的 IV/skew、盘口、basis、成本不是 Layer 2 缺口。

### 产物

```text
src/factor_lab/market_state/timing_layer2_measurement_plane.py
docs/ops/timing_layer2_measurement_plane@2.0.json
docs/schemas/json/timing_layer2_measurement_plane@2.0.json
docs/ops/timing_layer2_measurement_plane_whitepaper.md
tests/unit/test_timing_layer2_measurement_plane.py
```

### 停止门

- 17/17 资产覆盖；
- current source 数从实际 catalog 重算；
- 无 Layer 3/4 或共享冻结写入；
- 全部 authority fail closed。

## 6. 阶段 B：逐棒 PIT 核心 Provider

### B1：冻结公式的逐棒展开

先只展开已经存在并可精确对账的公式：

- 2/4/8/16 物理日效率、OLS t/R²；
- signed efficiency、signed OLS t；
- BDCI/BCI/WBI/DII；
- 单棒 body/range、上下影、CLV、Parkinson 和 Rogers-Satchell 充分统计。

Provider 按需计算，不一次物化全部 7×14×全历史。每个结果携带公共坐标和
质量元数据。

### B2：上下文窗测量

年度全样本统计不得直接冒充逐棒状态。return ACF、sign persistence、run length、
crossing density、volatility-of-volatility、down/up variance、jump share 和 gap/range
必须在事前声明的物理上下文窗族上发布；不得从策略结果选择唯一窗口。

### 对账门

- B1 点值与现有私有向量公式逐点一致；
- 对自然年取同样 reducer 后与年度 core extension 一致；
- 追加未来数据不改变历史前缀；
- 只读 qfq 信号面，不产生 fill 或 PnL。

## 7. 阶段 C：三组高价值测量族

### C1 量价与流动性

- amount/volume z-score、持续激活；
- volume-price coherence/divergence；
- turnover participation、Amihud 类 K 线流动性；
- 流动性收缩与恢复。

真实盘口 OFI/depth 不进入本阶段。

### C2 横截面结构

- 上涨/下跌广度、收益/成交额分位；
- 左尾、右尾、离散和集中度；
- 行业/动态群体纯度、leader concentration；
- 第二凝结核只在主控验收其测量语义后作为动态群体 Provider，不继承历史锚点
  日期或 winner 参数。

### C3 路径生命周期

- drawdown depth/velocity、reclaim margin；
- slope decay、curvature、channel compression；
- peak/trough/turn/reclaim age；
- failed reclaim 与 no-buffer reversal 的连续强度。

这些都是测量，不生成 low/normal/high 桶或交易动作。

## 8. 阶段 D：频谱相位年龄与滚动载体关系

### D1 频谱相位年龄

复用 IIR/Haar/brickwall/论文核，统一输出：

```text
component_energy
component_direction
phase_age
slope / acceleration
dominant_wavelength / confidence
cross_scale_lead_lag
group_delay
turn_age / reclaim_age
```

不选择 LAT 周期、IIR 参数或工具。

### D2 滚动载体关系

把年度 7×14 关系升级为滚动 PIT：correlation、beta、residual、relative strength、
tail dependence 和 lead-lag。动态成员变化必须绑定 membership_version。

## 9. 阶段 E：未来路径 Provider V2 与只读适配

### E1 Future Provider V2

在 V1 的 future RV/range/noise 基础上增加：

- future path efficiency/noise organization；
- jump/gap burden；
- 多期限、多载体；
- q10/q50/q90 的真实覆盖、校准和 abstention。

第一版仍不预测方向，不输出 PnL 或策略选择。

### E2 只读消费者

REAKA、绿波、Risk-Off、LAT、T0 分别只增加 adapter 和 parity test。adapter 只能
读取统一测量，不能在 Layer 2 内写阈值或动作。

## 10. current 与版本继承规则

1. 历史合同和 snapshot 永不覆盖。
2. 公式语义变化必须升 estimator 版本；只加 metadata 不改公式 digest。
3. 能力矩阵的 `current` 指向可机验合同，不以文档口述为准。
4. `cloudridge_daily_attributes_legacy` 标为 compatibility，不删除。
5. endpoint channel 只有在合同、测试、prefix 和 source closure 完整后才可继续
   current；否则标 `provisional_measurement_primitive`。
6. 属性池框架保持冻结；新 Layer 2 source 通过加法 overlay 发布新 snapshot。

## 11. 全局验收门

- 禁止列名/字段：`position`、`claim`、`action`、`selected_*`、`tool_owner`。
- `available_at >= observation_time`，时区和排序唯一。
- 前缀不变、尾部追加不改历史。
- 墙钟 bar 必须绑定 DataHub receipt；FactorLab 不本地重采样。
- 缺失、熔断、午休和成员变更不允许静默填 0。
- 旧公式重叠部分数值误差必须为 0 或在预注册浮点容差内。
- source registry/current pointer/文档 source 数一致。
- 最小测试、Ruff、BasedPyright、JSON Schema、`git diff --check` 全过。
- `fresh_oos=false`、`production_authority=false`。

## 12. 执行与汇报节奏

阶段严格串行。每阶段完成时输出：

1. 新增/变更身份；
2. 数值与时序门结果；
3. 未解决 incident；
4. 是否允许进入下一阶段；
5. authority 全量状态。

基础设施阶段可连续执行；一旦需要用策略收益选择测量公式、窗口或阈值，立即停止，
另开策略研究合同。

## 13. 完成记录

阶段A、B1、B2、C、D、E、F、G已全部执行。当前完成合同为
`timing_layer2_measurement_plane@2.1`。Future V2新增目标保持
`experimental_unvalidated`，第二凝结核未越过主控验收门；这两项诚实限制不影响
基础设施完成。最终current与验证证据从本计划对应的evidence目录读取。
