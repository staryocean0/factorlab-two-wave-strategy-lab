# v0.5.1 TCSS characteristic-scale 父级识别单组件实验：结果前冻结协议

日期：2026-09-05

协议状态：`frozen_before_v051_results`

操作基线：**v0.4.3，不变**。

上游表示候选：v0.5.0 TCSS，状态 `promotable_raw_reversal_representation_candidate`，但尚未成为父级识别器。

本轮只新增 **characteristic-scale identity + TCSS→raw-price parent projection**。资格函数、D1、有效信息时钟、互斥发布原则、数据范围全部冻结；不进入第三浪、收益、交易或生产。

## 1. 本轮唯一核心问题

v0.5.0 已证明：事前固定、严格因果的 TCSS 可以随尺度增加真正吞掉微摆；但它输出整个尺度空间，不能从 case_00 事后挑 `sigma=4` 或任何“最好看”的尺度。

本轮要回答：

> 能否仅用截至当时可获得的 TCSS 内部数学量，在不知道 case 标签、D1、IoU、资格结果或未来收益的前提下，为两浪候选自动产生可审计的 characteristic scale，并投影回原始价格的五个真实反转点，再交给冻结的资格/D1/互斥发布层？

如果不能，本轮必须否定该 selector；不得通过调整 case 专用阈值补救。

## 2. 理论依据：time-causal temporal scale selection

采用 Lindeberg 的 time-causal temporal scale selection 原则：在时间因果尺度空间中，对 **scale-normalized temporal derivative response** 寻找尺度维局部极大值，从而产生 characteristic temporal scale。

主要参考：

- Tony Lindeberg, *Temporal Scale Selection in Time-Causal Scale Space*, Journal of Mathematical Imaging and Vision 58, 57–101 (2017), DOI `10.1007/s10851-016-0691-3`。
- 对正弦型时间信号，n 阶尺度归一化导数的尺度极值满足 characteristic scale 与波长成比例；二阶导数采用文献常用 `gamma=3/4`。

本轮不是把金融价格假定成纯正弦，而是把该结果作为**事前、可解释、尺度协变的默认 scale-identity operator**。真实市场若不满足该局部模型，应通过 `uncertain/no characteristic scale` 暴露，而不是事后调参。

## 3. 冻结数学定义

沿用 v0.5.0 已冻结的 14 层半倍频程 TCSS 尺度格 `sigma_j`，不改尺度端点和层数。

### 3.1 单尺度五点候选

每个尺度 `j` 上仍只由五个交替、已确认 TCSS extrema 组成：

`p0 -> p1 -> p2 -> p3 -> p4`

其中 `p0,p1,p2` 与 `p2,p3,p4` 是两个相邻完整周期。

### 3.2 尺度归一化共同曲率响应

在每个候选自己的五个 TCSS extrema occurrence 时刻，用**只向后读取**的二阶差分：

`d2 L_j[t] = L_j[t] - 2 L_j[t-1] + L_j[t-2]`

高点使用 `-d2`，低点使用 `+d2`。若符号不支持该 extremum，则该点的尺度响应无效。

冻结 `n=2, gamma=3/4`，因此归一化因子为：

`tau^(n*gamma/2) = sigma^(n*gamma) = sigma^(3/2)`。

五点共同响应定义为五个正向归一化曲率响应的 **minimum**：

`Q_j = min_k sigma_j^(3/2) * signed_d2_j(p_k)`。

使用 minimum 而不是平均/最大值，是因为任务要求五个点共同属于同一尺度；任何一个相位没有尺度支持，都不能由其他四点补偿。

### 3.3 跨尺度候选家族 lineage

相邻尺度 `j-1 -> j` 只按结构位置和相位建立 lineage，不看价格收益、资格、D1、IoU 或人工标签。

TCSS 是因果滤波，尺度增大伴随延迟。仅用于**lineage 匹配**，不用于历史左移或信号时间补偿，定义延迟校正中心：

`center*_j = middle_occurrence_j - kernel_mean_age_j`。

对同相位候选按时间顺序做 one-to-one、order-preserving 最近邻匹配：

- 细尺度候选必须已经在该粗尺度候选 confirmation 时刻确认；
- 匹配距离 `|center*_j - center*_(j-1)| <= ceil(sigma_j)`；
- 同距离时按更早时间、稳定 ID 决定；
- 已匹配细候选不能被未来粗候选重新抢走；
- unmatched 粗候选产生新的 family，而不是强行跨远距离继承。

`ceil(sigma_j)` 是由当前平滑尺度给出的定位不确定性量级，不从 case_00、12–48 或任何结果倒推。

### 3.4 characteristic-scale 事件

一个 family 在尺度 `j` 成为 characteristic-scale，当且仅当：

- family 同时拥有 `j-1, j, j+1` 三个连续尺度成员；
- 三者 `Q` 均有效；
- `Q_j > Q_(j-1)` 且 `Q_j >= Q_(j+1)`。

右侧允许相等、左侧严格，是固定 plateau tie-break：若尺度响应平台相等，选择**更细/更低延迟**的一侧。

characteristic-scale 的确认时间不是尺度 `j` 自己的完成时间，而是：

`max(confirm_(j-1), confirm_j, confirm_(j+1))`。

因此必须等到相邻更粗一级也已经确认，才能知道 `j` 是尺度维局部极大值；禁止把这个尺度身份回填到更早时间。

尺度格最细和最粗边界没有双侧邻居，**不得**直接产生 characteristic-scale，避免把网格边界误认成极大值。

一个 family 可以在不同尺度出现多个真正的局部极大值；这表示多尺度结构，不强制全局唯一赢家。后续冻结资格层决定当前目标时间带是否合格。

## 4. TCSS 候选投影回 raw price

最终金融语义仍是 `raw-price reversal wave`，所以不能把平滑价格 extrema 直接当成真实边界。

对 characteristic member 的五个 filtered extrema `t0...t4`，在**该 member 自己原始 confirmation 时刻**冻结 raw projection；后续等待 scale-selection confirmation 不能扩大 raw 搜索区间。

固定顺序投影：

1. 第一点的左界为 `max(0, 2*t0 - t1)`，即按第一段 filtered 间距向左对称扩一段；
2. 五个搜索上界依次为 `t1-1, t2-1, t3-1, t4-1, member_confirmation`；
3. 从左到右依次在 raw close 中寻找对应 high 的最大值 / low 的最小值；
4. 同价 plateau 取最后一个 occurrence，与现有 causal plateau 语义一致；
5. 下一点搜索从上一 raw occurrence + 1 开始，保证严格时序；
6. 若无法形成五个严格有序且价格方向真实交替的 raw extrema，记录 `raw_projection_invalid`，不得强行修补。

投影使用的 raw 点在 member confirmation 时已经全部存在，因此未来数据不能改变它们。

最终 parent recognition confirmation 取 characteristic-scale confirmation；因此总延迟包含：

- TCSS 核延迟；
- extremum turn confirmation；
- 等待相邻更粗尺度确认的 scale-selection delay。

不做任何历史左移补偿。

## 5. 下游组件全部冻结

raw projection 成功后，直接调用 v0.4.3 冻结的 `evaluate_pair` / `MaturityConfig`：

- `min_leg=4`
- `min_cycle=12`
- `max_cycle=48`
- `max_pair=96`
- 现有 duration/amplitude/path/day/wall-time/confirmation-delay 资格规则全部不改；
- D1 不改。

这里 `12–48` **只在 characteristic scale 已经独立产生之后**作为目标周期资格层；不得参与 TCSS family 建立、Q 计算或 characteristic-scale 选择。

这一区分是本轮核心：

- hierarchy/scale identity：由 TCSS + normalized derivative scale maximum 给出；
- target-band qualification：由冻结的 12–48 等规则给出。

## 6. 多候选冲突与互斥发布

所有已确认、已 raw-project、已 evaluate 的记录按：

1. `characteristic_confirmation_bar` 更早；
2. 同一确认时刻时 characteristic scale 更细；
3. 再按更早 start/end 与 stable ID；

确定性排序。

之后复用 v0.4.3 的原则进行 causal greedy non-overlap packing：

- 只允许 `scale_qualified=true` 发布；
- 已发布区间不被未来更漂亮对象改写；
- 不按 D1、通道拟合、IoU、覆盖率或收益排序。

## 7. 结果前硬门

### 合成硬门

必须先过：

- 严格单调 raw price：0 characteristic raw two-wave；
- 单一正弦族（多个固定波长）：characteristic sigma 随波长单调增加，不允许所有周期都选同一尺度；
- `drift + visible reversal sine`：保留 raw reversal；
- `parent + child oscillation`：必须允许父/子产生不同 characteristic scales，不能只剩 child，也不能只靠删空；
- jump：不得产生合格 raw two-wave；
- prefix append：已确认 family / characteristic event / projected raw points / selected publication 不得被未来重写。

### 真实数据

仍只用冻结观察面：

- case_00 / 02 / 10 / 11 / 14；
- 2018-06-20 / 2019-04-15 / 2020-07-15；
- 五个原生 5m offset；1m 仅诊断。

必须执行六视图 × 25/50/75% = 18 次固定前缀重放。

### 本轮新增可判定指标

由于本轮首次有自动 characteristic scale + frozen qualification + unique causal publishing，允许正式恢复：

- 五个原生 5m 相对 `offset_0` 的发布区间 IoU；
- characteristic scale 分布；
- raw projection 成功/失败率；
- characteristic candidate → qualified → selected 漏斗；
- 总确认延迟与 scale-selection 增量延迟；
- 每个发布对象内部吸收的 v0.4.3 额外局部极值。

**IoU 仍是边界稳定性，不是形态准确率。**

## 8. 晋级判定

v0.5.1 只有同时满足以下条件才可以升级为新的 morphology candidate：

1. 合成尺度选择语义通过；
2. 18 次真实前缀零重写；
3. case_00 不再依赖人工选择 sigma，并确实形成父级粗化后可解释对象；
4. case_02 不复活 90/3 或 1–3 根假浪；
5. case_11/14 的粗尺度巨型结构不能穿过冻结资格层成为发布对象；
6. 2019 不靠删空解决，2020 不出现无解释全损失；
7. offset 稳定性至少不能相对 v0.4.3 出现四项一致性显著退化；
8. 总确认延迟必须完整报告，不能用历史左移掩盖。

若 selector 过严导致几乎无对象，不能把低覆盖当准确率；若 selector 过松导致多尺度重复/巨型结构穿透，也必须否定。

## 9. 明确禁止

- 不看 case_00 后改 `gamma=3/4`；
- 不看结果后改 family gate；
- 不用 12–48 反推 TCSS characteristic scale；
- 不按 D1、IoU、收益挑尺度；
- 不修改 v0.4.3 资格或 D1；
- 不进入第三浪、收益或交易。

PR #1 继续 Draft，main 不合并。
