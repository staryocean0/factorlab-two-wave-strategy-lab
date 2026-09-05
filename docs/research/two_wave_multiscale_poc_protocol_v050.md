# v0.5 多尺度父级波形 POC：结果前冻结协议

日期：2026-09-05

协议状态：`frozen_before_multiscale_poc_results`

依赖预研究：`docs/research/two_wave_multiscale_pre_research_v050.md`

操作基线：**v0.4.3**。本协议只授权表示层/父级候选构造 POC，不建立新基线，不改资格/D1，不进入收益、第三浪、交易或生产。

## 1. 本 POC 要回答的唯一问题

> 是否存在一个**事前冻结、实时因果、可形成真正尺度层级**的数学表示，使我们能够在同一尺度上识别相邻的两个完整价格波形，并让造成 v0.4.4 碎片化的更细摆动在更粗尺度被系统吸收，而不是依靠绝对根数闭合、事后选漂亮五点或简单删除候选？

这一轮不回答“这个结构能不能赚钱”。

## 2. 先冻结最容易跑偏的语义：原价格反转 vs 去趋势周期

用户原始合同要求明确区分：

- **raw-reversal wave**：原价格路径确实发生反转；
- **detrended-cycle wave**：原价格即使单调，去掉漂移后仍可有周期。

本项目 v0.4.x 一直在识别原价格路径的实际反转。为了让 v0.5 与既有失败证据可比较，**首轮生产晋级语义继续冻结为 raw-reversal wave。**

因此对反例

`x(t) = b t + A sin(omega t)`

当 `b > A*omega` 且离散样本保持严格单调时，生产候选**不得为了凑两浪而凭空输出原价格完整反转**。允许输出“该尺度下无两个 raw-reversal complete waves”。

这条规则对方法选择有直接影响：

- time-causal scale-space 的 variation-diminishing / 不新增极值性质与 raw-reversal 语义天然一致；
- SSA 的 oscillatory reconstructed component、wavelet detail/band-pass、EMD IMF 即使在原价格单调时也可能存在振荡。若它们只在残差/模态上有两浪，必须标记为 `detrended_cycle_only`，**不能与 raw-reversal 结果混为一个指标，也不能直接晋级当前生产定义**；
- 若 SSA/wavelet 要进入 raw-reversal 主赛道，模态只能用于尺度提示/去噪，最终五个父级极值必须有可审计的原价格反转支撑，且不能由未来对齐。

未来可以另立一个独立实验研究 detrended-cycle 语义，但不能在本轮偷偷切换目标。

## 3. 数据与视图冻结

不新增、不下载、不重采样任何行情。

- 主对象：`000852.SH`，原生 `5m_offset_0`；
- 稳健性：其余四个原生 5m offset；
- `1m_official`：只做诊断；
- 数据：仓库现有 2015-01-05 至 2020-12-31 development material；
- 输入价格：与 v0.4.3 形态链一致，以已有 bar close / log-price 口径进入表示层，不引入 OHLC 同根内部顺序假设；
- 既有 DataHub 时间戳与 `available_at`/有效信息时钟规则不变。

既有 `12—48` 只在结果阶段作为**目标周期资格/诊断带**报告，绝不能参与父级尺度闭合或尺度选择。

## 4. 结果前方法角色冻结

### A. `TCSS`：time-causal scale-space，raw-reversal 主候选

目标：直接测试“尺度增加时微极值消失、较粗结构保留”的父级机制。

实现合同：

1. 必须使用一维时间因果、时间递归的 scale-space 核；不得用 Gaussian 双边卷积、`filtfilt` 或中心化窗口。
2. 尺度层构成**事前固定的几何尺度格**，而不是根据 case_00 或结果动态选出一条最漂亮的尺度。
3. 具体时间常数按 Lindeberg time-causal scale-space 的离散递归构造从尺度格**确定性导出**；实现提交必须把推导和参数写入代码/报告。
4. 每个尺度层上的极值只通过当时已经出现的方向变化确认；plateau 用确定性规则处理，并保存 occurrence 与 confirmation 两套时钟。
5. 不把滤波后的极值 occurrence 倒移补偿群延迟。滤波器内部延迟和极值确认延迟分别报告。
6. 同一尺度上五个交替已确认极值才构成两个完整周期。
7. 所有尺度层都输出审计结果；首轮**不按视觉、IoU、D1 或收益选唯一最佳尺度**。
8. 对每个父级周期，叠加 v0.4.3 局部极值 lineage，统计该父周期内部有多少已确认 v0.4.3 细极值被更粗尺度吸收。v0.4.3 pivot 只作 audit overlay，不控制 TCSS 的闭合。

首轮尺度格冻结原则：使用**几何/对数间隔**覆盖从明显局部到明显父级的多个尺度，端点由数据频率/计算支持预先设定，不以 `12—48` 作为闭合门槛。若实现需要选具体离散层数，必须在任何真实 case 结果生成前提交到本协议的执行子协议，并一次性报告所有层。

### B. `tSSA`：trailing/causal SSA，语义分流候选

目标：检验碎片是否可被解释为低频振荡 + 高频扰动，同时证明在线版本不会重画历史。

实现合同：

1. 只能用 trailing window；每个时间 t 的分解只读 `<= t`。
2. 不能把每次新窗口得到的完整 reconstructed component 回填覆盖旧事件；只能在当前边缘产生新 provisional/confirmed 状态。
3. 计算窗口属于算法支持域，**不是父浪长度定义**。
4. eigentriple 分组/振荡分量选择必须事前固定为确定性规则；不能看 case 后挑分量。
5. 首轮必须同时输出两类标签：
   - `raw_reversal_supported`：最终父级极值有原价格反转支撑；
   - `detrended_cycle_only`：只在 RC/残差中存在周期。
6. 只有前者有资格与 TCSS 的 raw-reversal 主指标比较；后者只说明“另一种金融语义可能有价值”。
7. 若固定前缀重放显示已确认历史随未来窗口推进发生变化，tSSA 立即降级为 offline oracle，不再争夺生产候选。

### C. `cWAV`：causal multiresolution wavelet/filter bank，语义分流候选

目标：检验事前固定的多频带/多尺度局部表示是否能稳定提取父波。

实现合同：

1. 只允许单边实时滤波，例如 `lfilter`/递归滤波；禁止 `filtfilt`、中心化 CWT 或任何未来 padding。
2. 频带/尺度格在结果前固定，并全部报告；不按 case 选频带。
3. 必须报告群延迟/相位延迟，不做事后左移对齐。
4. jump/ringing 合成反例是硬测试：滤波振铃不能被误当成原价格两浪。
5. 与 tSSA 相同，输出 `raw_reversal_supported` 与 `detrended_cycle_only` 两套语义，禁止混算。

### D. Oracle/reference/control，不参与首轮生产晋级

- `PERSISTENCE`：测试相对持久性层级是否能给出更合理的离线父子排序；若没有严格 prefix-native 配对，不产生生产事件。
- `EMD/EEMD`：只做离线自适应模态 oracle；报告 mode mixing、端点敏感性，不把 IMF 回填成实时两浪。
- `SST/VMD`：只做离线模态分离参照。
- `DC`：event-time control，证明“换成事件时间阈值”本身能否解决问题；不把阈值层级当父级真理。
- `CPD`：本轮不参与两浪候选构造。

## 5. 合成数据硬测试：先于真实 case

所有方法先过以下合成族。随机测试固定 seed，并保存生成参数；不得看到结果后修改生成器只保留有利例子。

### S0：严格单调

- 线性上涨/下跌；
- `b > A*omega` 的漂移正弦，使离散原价格保持严格单调。

**raw-reversal 期望：0 个完整两浪。**

任何方法若因滤波振铃/模态残差输出 raw-reversal 两浪，属于语义失败。

### S1：单一干净周期

`x(t) = A sin(omega t)` 加少量确定性噪声。

验证：

- 完整周期计数；
- 同尺度身份；
- occurrence/confirmation 延迟；
- prefix invariance。

### S2：漂移 + 可见真实反转周期

`x(t)=b t+A sin(omega t)`，取 `0 < b < A*omega`。

验证：方法能在有方向漂移时仍保留实际高低反转，而不是把趋势去掉后只输出水平周期。

### S3：父周期 + 高频子摆

`x(t)=A_p sin(omega_p t)+A_c sin(omega_c t)`，`omega_c >> omega_p`，并覆盖多个固定幅比/频比。

这是 v0.4.4 核心失败的数学化反例。验证随尺度增加：

- 细极值减少；
- 父周期仍可形成；
- 不通过“全部删光”获得粗化；
- 父层内部可记录被吸收的子层 extrema。

### S4：非平稳 chirp / 缓慢周期变化

验证“同尺度”不是强制两个周期完全等长；方法应在特征尺度缓慢变化时给出可解释的尺度轨迹或不确定状态。

### S5：单次跳跃 + 噪声

验证 wavelet/filter ringing、EMD 端点/模态和 SSA 重构不会把单跳错误生成为两个 raw-reversal 周期。

### S6：振幅突变/间歇振荡

验证 mode mixing、尺度切换和 provisional tail。

## 6. 因果性与历史不可重写硬门

任何生产候选必须：

1. 全序列 streaming 输出；
2. 对相同序列 25%/50%/75% 固定前缀分别运行；
3. 在前缀末端之前，对**已经 confirmed** 的事件逐字段比较：ID、成员、occurrence、confirmation、scale identity、lineage、分类输入都必须一致；
4. 允许不同的只有明确 provisional tail；
5. 追加未来数据不得改变 confirmed 历史。

真实数据继续执行既有六视图 × 25/50/75% = **18 次固定前缀重放**。

若一个方法只能保证“最终离线结果大致相似”而不能满足逐事件 prefix invariance，它自动降级为 oracle/reference。

## 7. 真实数据比较：固定观察面，不新增 case

首轮仍使用已经在仓库冻结的观察面，避免研究者自由挑图：

- case_00：v0.4.4 核心碎片化失败；
- case_02：90/3 假浪安全反例；
- case_10：候选存在但 D1 uncertain，只观察表示层，不借机改 D1；
- case_11 / case_14：防止重新退化成跨数周巨型五点；
- 2018-06-20：规整 `11/13/15/14、24/29`，资格 `inefficient_leg` 保持原样；
- 2019-04-15：防止“只删除坏对象却没造出父结构”；
- 2020-07-15：防止无解释丢掉 v0.4.3 已有可解释 downtrend 对象。

不得新增“特别好看”的窗口用于晋级；若研究过程中发现新反例，可以加入**失败档案**，但不能只加入有利正例。

## 8. 评价量冻结：不看收益

### 8.1 `hierarchy_coarsening`

- 每个父级周期/两周期结构内部覆盖的 v0.4.3 已确认局部极值数；
- 被父级表示吸收的内部细极值数；
- 父/子 extrema ratio；
- 随尺度增大 extrema 数是否单调不增（TCSS 为理论/实现一致性硬检查）。

候选减少不是成功；**必须区分“吸收微摆”和“删掉整个对象”。**

### 8.2 `two_complete_wave_validity`

- 两周期必须共享中间同相位端点；
- 五点交替；
- 两周期来自同一尺度身份；
- scale identity/selection reason 可审计；
- 不强制等长等幅，但报告周期比、振幅比、尺度漂移。

### 8.3 `raw_reversal_semantics`

- `raw_reversal_supported` 数量与覆盖；
- `detrended_cycle_only` 单独计数；
- 严格单调合成数据 raw-reversal false-positive 必须为 0。

### 8.4 `prefix_stability`

- 18 次固定前缀逐事件一致率；
- confirmed event rewrite count；
- provisional tail 长度。

生产候选的 confirmed rewrite count 必须为 **0**。

### 8.5 `native_5m_boundary_stability`

仍将五个原生 5m offset 的结构区间映射到既有 1m 时间戳做边界比较，不合成新 K 线。

报告：

- 相对 `5m_offset_0` 的区间 IoU；
- 各视图覆盖率；
- 结构边界时间差；
- 不允许用覆盖率变化解释 IoU。

### 8.6 `latency`

分别报告：

- 算子/滤波延迟；
- extrema reversal confirmation delay；
- 两周期完成确认延迟；
- 最终结构可用时间。

不做离线时间轴左移。

### 8.7 `safety_regression`

case_02、case_11/14、jump synthetic 不得用“更大尺度”重新制造明显错误的巨型/振铃两浪。

## 9. 晋级规则冻结

比较顺序是**词典序硬门**，不是加权总分：

1. 金融语义正确；
2. confirmed prefix rewrite = 0；
3. 能证明存在真实层级粗化，而不是删除；
4. 旧安全反例不退化；
5. case_00 / 固定窗口出现机制上可解释的改善；
6. 五个原生 5m 边界稳定性；
7. 确认延迟和覆盖成本。

前一层失败，不能靠后一层漂亮补偿。

**没有“至少选一个赢家”的要求。** 如果 TCSS/tSSA/cWAV 全部不能同时满足金融语义和因果性，本轮结论应为 `all_candidates_rejected`，继续寻找新的数学表示。

## 10. 首轮预计判定类别

每条路线只能进入以下之一：

- `promotable_raw_reversal_representation_candidate`
- `useful_but_detrended_semantics_only`
- `offline_oracle_only_due_to_repainting`
- `rejected_due_to_no_true_hierarchy`
- `rejected_due_to_safety_regression`
- `rejected_due_to_implementation_or_contract_failure`

即使进入第一类，也**不等于 v0.5 基线已接受**。仍需独立形态标签/人工审查和后续正式单组件实验。

## 11. 实现顺序与安全停点

1. 先提交本协议；
2. 添加合成数据与公共 causal/prefix 测试 harness；
3. 独立实现 TCSS、tSSA、cWAV，不共享结果驱动参数；
4. 先跑 synthetic gate；
5. synthetic 通过后才跑固定真实窗口；
6. 再跑全样本六视图与 18 次 prefix replay；
7. 生成并归档全量结果，无论正负；
8. 再决定是否有方法值得进入一个正式的“单组件新版本”。

在第 8 步之前：

- **v0.4.3 继续是操作基线**；
- 不创建/宣称 v0.5 生产基线；
- 不调资格、D1；
- 不看收益；
- PR #1 继续 Draft；
- 不合并 main。
