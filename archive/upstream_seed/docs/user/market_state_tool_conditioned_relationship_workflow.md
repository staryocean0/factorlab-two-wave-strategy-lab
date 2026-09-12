# 逐工具 K线属性条件关系认证工作流

版本：1.3

适用范围：市场状态中台 R2 之后、动态调参或工具路由之前

当前状态：`completed_tool_conditioned_small_factor_and_joint_prototype_audit`

默认权限：不授予动态参数、工具路由或生产权

## 1. 这一层解决什么

第二代 R2 已经证明：部分公式倒推因子能够解释某些具体参数对的相对收益，
但把所有工具、参数和频率混在一起后，没有形成“跨配对普遍规律”。

这并不能推出“属性与工具无关”。缺失的问题是：

> 固定某一个具体工具、载体周期和参数语义轴后，K线属性增大时，该参数应
> 往上调还是往下调；这种方向能否在时间外稳定复现？

本层只认证这个逐工具条件关系。它既不要求不同工具同向，也不允许用一个
孤立参数点代替完整关系。

## 2. 五位一体权威

| 层 | 权威产物 |
| --- | --- |
| 文档 | 本工作流 |
| 白皮书 | [`market_state_tool_conditioned_relationship_whitepaper.md`](../ops/market_state_tool_conditioned_relationship_whitepaper.md) |
| 代码 | `tool_conditioned_relationships.py` |
| 测试 | `test_market_state_tool_conditioned_relationships.py` 与 `test_market_state_tool_authority_consistency.py` |
| 工作流 | R2训练折系数持久化 → 账户角色去重 → 镜像参数复现 → 对角反证 → 工具内及跨工具多重检验 → 独立复算 |

机器契约为
`market_state_tool_conditioned_relationship_research@1.0`。

## 3. 输入边界

输入只允许来自已经验证的第二代 R2 包：

```text
output/market-state-foundation/formula-mechanism/
  r2-mechanism-validation/
```

并绑定冻结的 3×3 工具参数字典：

```text
output/market-state-foundation/fixed-capability/r1/
  tool_fixed_parameter_dictionary.json
```

本层不重新扫描行情。研究期仍是 2009—2020，2021—2026 必须保持：

```text
derived_market_data_rows_read = 0
post_2020_rows_used = 0
blackbox_detail_opened = false
```

## 4. 为什么要补存训练折系数

R2 原输出只保存了选择器的时间外收益，却没有保存训练折学到的因子系数。
因此它能回答“这次选择赚没赚钱”，却不能回答：

```text
属性上升 → 更长周期更好
```

还是：

```text
属性上升 → 更短周期更好
```

R2 现在必须在每个外层训练折保存：

- `train_factor_coefficients_json`；
- `train_factor_coefficient_signs_json`。

系数只由当时训练段估计，绝不能用验证折或 2021—2026 反推。

## 5. 独立票如何定义

### 5.1 做多与空仓只算一票

同一参数分歧产生的 `long_capture` 与 `cash_avoidance` 相对差是同一仓位差
的两种记账语言。代码必须逐事件核对时间边界及相对目标完全一致，再折叠为
一个 `role_collapsed` 票。禁止把它们当作两次独立复现。

### 5.2 相同因子、相同尺度只算一票

同一个因子可能被多个公式机制引用。若 `factor_id + primary_scale_id`
相同，则无论列入几个机制或代理家族，统计上只算一个假设；机制列表只用于
解释和追溯。

## 6. 镜像参数认证

每个工具—频率的冻结参数面有两个语义轴：

- `timescale`：时间尺度；
- `shape`：响应形状、带宽或通道宽度。

正式关系只使用四个纯轴参数点：

```text
(-1, 0), (+1, 0), (0, -1), (0, +1)
```

### 6.1 当前单因子阶段不要求 100% 命中

当前基础设施还不能把其他属性的条件影响完全剥离。单因子 \(x\) 有效，
不表示所有事件都只由 \(x\) 决定。因此不能用“100 个事件必须 100 个都
符合”作为门槛。

本层只统计样本外期间因子模型真正改变冻结固定参数选择、且两种选择收益差
非零的事件：

```text
条件命中率 =
  改选后选择正确的事件数
  / 因子触发的非零改选事件数
```

冻结分层为：

- `partial_70_80`：70%—80%；
- `moderate_80_90`：80%—90%；
- `strong_90_95`：90%—95%；
- `very_strong_95_plus`：95%以上。

高比例但只有两三次改选不能通过。合格参数侧还必须：

1. 至少 20 个非零改选事件；
2. 改选事件分布在至少 3/4 外层折；
3. 至少 3/4 折净改善为正；
4. 至少覆盖 6 个样本外年份；
5. 至少 70% 的可用年份净改善为正；
6. 相对训练期冻结的固定冠军，整体方向准确率必须提高；
7. 允许 4 个外层折中最多 1 个出现实质性反向，承认其他因子干扰；
8. 训练系数符号、形状族、尾部集中度和简单模型门仍须通过。

这里的 70% 是当前单因子条件关联门，不是生产胜率承诺。

### 6.2 完整参数方向仍需要镜像

对某一轴，负侧与正侧必须分别相对基准 `(0,0)` 通过上述单因子门，并满足：

1. 两侧都达到至少 70% 的单因子条件命中；
2. 正负侧的归一化训练系数同号；
3. 变换形状族一致；
4. 八个样本外年份完整；
5. 年度改善不由单一尾部主导。

正侧的训练系数保持原符号；负侧系数乘以 `-1`。只有两个归一化符号
一致，才能说属性变化稳定地指向参数轴上调或下调。

## 7. 八个样本外年份和多重检验

四个外层折的验证年份为 2013—2020，共八个互不重叠年度时间块。
镜像两侧对同一年取中位改善，再做完整枚举的一侧 sign-flip 检验。

统计纠错分两层：

1. 同一工具内，对该工具全部预注册关系做 Benjamini–Hochberg；
2. 每个工具先用 Simes 形成工具总检验，再对 13 个工具做
   Benjamini–Hochberg。

只有两层 `q <= 0.10`，关系才可记为
`stable_tool_conditioned_relation`。没有通过不允许靠删除失败假设缩小
检验家族。

## 8. 对角参数只用于反证

`(-1,-1)`、`(-1,+1)`、`(+1,-1)`、`(+1,+1)` 同时改变两个参数轴，
不能当作纯轴关系的支持票。

它们只做反证：若至少三个充分对角候选中，75% 以上系统性给出与主关系
相反的归一化系数方向，则主关系记为 `rejected`。对角证据不足不会自动
加分，也不会伪造复现。

## 9. 结论层级

- `stable_tool_conditioned_relation`：镜像、跨年和两层多重检验均通过；
- `replicated_but_multiplicity_unconfirmed`：跨年复现，但完整家族纠错未过；
- `one_sided_single_factor_association`：参数一侧通过 70% 起步的当前
  单因子门，但另一侧没有形成完整参数方向；
- `rejected`：两侧不一致或被对角候选系统反证；
- `insufficient_support`：没有足够独立事件。

即使第一类存在，它仍只是参数研究证据，不是可直接上线的动态公式。

## 10. 执行

先重建带训练折系数的 R2：

```bash
PYTHONPATH=src uv run python \
  scripts/build_market_state_tool_mechanism_validation.py \
  --output-dir \
  output/market-state-foundation/formula-mechanism/r2-mechanism-validation \
  --profile-workers 8 \
  --validation-workers 8

PYTHONPATH=src uv run python \
  scripts/validate_market_state_tool_mechanism_validation.py \
  --output-dir \
  output/market-state-foundation/formula-mechanism/r2-mechanism-validation
```

再构建中间层：

```bash
PYTHONPATH=src uv run python \
  scripts/build_market_state_tool_conditioned_relationships.py

PYTHONPATH=src uv run python \
  scripts/validate_market_state_tool_conditioned_relationships.py
```

独立验证器会重新计算年度 sign-flip、工具内 BH、工具 Simes、13 工具 BH、
对角反证和最终状态，而不是只相信构建器写出的结论。

## 11. 输出

权威结果目录：

```text
output/market-state-foundation/formula-mechanism/
  tool-conditioned-relationships/
```

主要产物：

- `tool_conditioned_authority.json`；
- `hypothesis_registry.json`；
- `role_deduplication_audit.parquet`；
- `role_deduplicated_fold_evidence.parquet`；
- `hypothesis_fold_evidence.parquet`；
- `primary_side_summary.parquet`；
- `diagonal_candidate_summary.parquet`；
- `diagonal_challenge_summary.parquet`；
- `tool_factor_relation_matrix.parquet/csv`；
- `tool_summary.parquet/csv`；
- `data_usage_ledger.json`；
- `source_lineage.json`；
- `artifact_inventory.json`；
- `report_zh.md`。

## 12. 2009—2020 已执行结果

本层已完整执行并由独立验证器复算：

- 输入第二代 R2 的 282,034 个完整分歧事件、43,720 条外层折证据；
- 覆盖 13 个工具、23 个工具—频率镜头、698 条预注册关系；
- 1,396 个纯轴参数侧中，56 个表面命中率达到 70%，但大多数只有
  1—11 次真实改选，不能凭小样本升格；
- 只有 2 个属性标签同时通过至少 20 次改选、3 个外层折、6 个年度及
  70% 条件命中门；
- 两者均属于 `rolling_fourier_bandpass`、`1d`、shape `+1` 相对基准：
  41 次非零改选中 29 次正确、12 次错误，命中率 70.7317%，四个外层折
  均有动作，8 个年份中 6 年净改善为正；
- 该侧共有 118 个样本外分歧事件，因子实际改选覆盖 34.75%；全事件方向
  准确率由固定冠军的 41.53% 提升到 55.93%，因此 70.7317% 是有动作时
  的条件命中率，不是全部事件的无条件胜率；
- 两个标签是 `directional_run_age` 与 `residence_fraction`。在固定
  60 日尺度上后者严格等于前者除以 60，逐折决策证据完全相同，因此只能
  算 1 个独立单侧条件关联；
- 对应 shape `-1` 侧的条件命中率只有 43.75%，所以 0 条关系形成完整
  镜像参数方向，0 条获得动态调参或路由权；
- 2021—2026 读取 0 行，未做拆解、归因或选参。

当前可以认下的不是“两个独立因子”，而是：

> 当日线方向驻留已经较长时，滚动傅里叶带通的 shape `+1` 候选
> （`high_period_bars=72, low_period_bars=23`）相对冻结基准
> （`80/20`）存在一个 70% 档、跨折跨年的单侧条件关联。

它尚不能推出 shape 参数随方向驻留单调上调，因为镜像的另一侧没有证据。

## 13. 未来多因子层的“100%”

未来可以要求多因子层对 100% 的事件完成归因记账：

```text
已解释主效应 + 条件交互 + 明确冲突因子 + 显式未解释残差 = 全部事件
```

但不能要求交易预测命中率达到 100%。金融市场存在不可观测信息、跳跃和
执行噪声；把“100% 记账覆盖”误写成“100% 预测正确”，只会制造过拟合。

## 14. 少因子并行研究层

当一个单侧关系或近候选已经出现时，不再将整个因子库一次性塞入
同一个搜索。每个研究单元必须预先冻结：

1. 一个具体工具、载体周期和参数侧；
2. 一个既有锚点；
3. 最多三个有数学、物理或市场结构先验的修饰因子；
4. 折内中位数或一个预声明分位点，禁止阈值网格海搜；
5. 完整的小检验家族和线内 BH 纠错，不得只留最好看的结果。

通过候选除了满足第 6 节的单侧关系门，还必须相对既有锚点提供
正的年度时间外边际。别名、共用分子和确定性单调变换只能算一张
信息票。通用 K 线代理只能书写为通用代理相关，不能冒充工具原生机制。

### 14.1 本轮三个研究单元

| 研究单元 | 预登记小因子组 | 结果 |
| --- | --- | --- |
| 滚动傅里叶日线 shape `+1` 持续性残差 | 通用信噪代理、BDCI、下行半方差 | 3 个全部排除 |
| Laplace IIR 60m timescale `-1` | BDCI、本尺度激活、邻频激活比 | 3 个全部拒绝；邻频激活比保留为观察线索 |
| 滚动傅里叶日线 timescale `-1` | 能量份额、边缘泄漏、本尺度激活 | 1 个预声明交互拒绝；前两者合并为一票 |

合计审计 7 个预声明候选，新认证因子数为 0。既有
`directional_run_age` 单侧关系仍然有效。这不表示“市场中没有更多
因子”，只表示这三个小家族不得升格。

### 14.2 强制失败台账

- 每条研究线必须保留正确/错误动作数、年度结果、`p`、`q`、边际收益和
  拒绝原因；
- 保留“语义错位”：目前 `signal_margin_to_noise` 是通用价格代理，
  不是 IIR 决策变量到边界的距离；
- 保留“公式错位”：目前 `transfer_weighted_energy_share` 没有使用
  候选工具的频响应权重，只是固定频带能量份额代理；
- 完整证据见
  [`market_state_small_factor_parallel_research_20260730.md`](../ops/evidence/market_state_small_factor_parallel_research_20260730.md)；
- 独立验证命令：

```bash
uv run python scripts/validate_market_state_small_factor_lanes.py --rerun-lanes
```

## 15. 多因子联合状态机原型

单因子门回答的是“其他状态未被完全剔除时，这一个局部偏导是否
稳定存在”，不是完整的动态参数公式。降低或提高单因子命中阈值，
不能解决遗漏变量和因子交互。

联合原型必须依次执行：

1. 固定一个工具、频率和一对已登记参数；
2. 只使用该工具公式因果链倒推出的少量因子；
3. 先做确定性别名审计，再做相关族审计；
4. 预声明公式或状态结构，只在每个外层训练折估计标准化量；
5. 同时对照训练折固定冠军和已认证最佳单因子；
6. 联合模型未提供相对单因子的时间外边际时，必须停止，不得改阈值补考。

### 15.1 已执行的第一版

原型固定为日线 `rolling_fourier_bandpass` 的窄带 `23–72/256`
相对基准 `20–80/256`。三个预声明状态量均在 `medium_60d`：

- `directional_run_age`；
- `own_scale_activation`；
- `neighbor_activation_ratio`（实现量为 `RV_60/RV_120`）。

每个量高于外层训练折中位数记一票，至少两票时选窄带。该规则
未搜索因子、方向、分位、投票数或权重。

样本外结果：

- 最佳单因子：41 次改选，29 对 / 12 错，命中 70.73%，相对固定净增益 `+0.05170868`；
- 联合状态机：51 次改选，27 对 / 24 错，命中 52.94%，相对固定净增益 `-0.11223837`；
- 联合状态相对最佳单因子边际 `-0.16394705`，只有 2/4 折和 2/8 年份为正；
- 年度边际精确符号翻转 `p=q=0.859375`，故裁决为 `rejected`；
- 2021—2026 读取 0 行。

这不否定“多因子联立”本身，它否定了“相关因子平铺后等权投票”。
`own_scale_activation` 与 `neighbor_activation_ratio` 的事件级 Spearman
为 `0.7116`，虽非确定性别名，却明显共享频谱激活信息。将它们各算
一票，等于让同一机制重复加权。后续若立项，必须先把因子压缩为
“持续性块”与“频谱激活块”，再验证块间交互，不得继续平铺投票。

完整证据：
[`market_state_multifactor_state_machine_prototype_20260730.md`](../ops/evidence/market_state_multifactor_state_machine_prototype_20260730.md)。
独立验证：

```bash
PYTHONPATH=src python \
  scripts/validate_market_state_multifactor_state_machine_prototype.py
```
