# v0.5 多尺度父级波形识别：跨学科预研究与数学适配性筛选

日期：2026-09-05

状态：`pre_research_frozen_before_poc_results`

当前操作基线：**v0.4.3**。本文件不是新基线、不是形态验收、不是收益研究，也不授权第三浪、交易或生产部署。

## 0. 为什么先做这一轮，而不是直接写 v0.4.5

v0.4.4 已经正式排除了一类自然但错误的父级构造：把既有 `12—48` 根绝对周期资格带前移为“父周期闭合”规则。case_00 中造成碎片化的局部周期本身就大量落在 13、16、17、19、25 根，因此“第一次进入绝对允许带就闭合”只能抽取局部链，不能建立父子尺度。

本轮因此先把问题从“怎么调 ZigZag/周期参数”改写成一个更基本的数学问题：

> **在时间 t，仅使用截至 t 可获得的信息，从非平稳价格序列中建立一个有层级的多尺度表示；在某个共同尺度上识别相邻、完整的两个振荡周期，再用它们的整体漂移/包络几何判断父结构是震荡、上涨趋势、下跌趋势或不确定。**

“方法能把曲线分解得漂亮”不构成合格。任何方法若依赖未来样本、中心化窗口、全样本端点延拓、事后择尺度，或会在追加未来数据后重写已确认历史，即使离线图形很好，也不能作为生产候选。

## 1. 金融需求先于算法：本轮硬合同

### 1.1 输出对象必须真的是“两浪”，不是一个窗口标签

低点起算：

`L0 -> H1 -> L1 -> H2 -> L2`

高点起算对称。`L0-H1-L1` 与 `L1-H2-L2` 是两个完整周期，共享中间同相位端点。不能把两条单向腿称为两个完整波浪。

### 1.2 “同尺度”必须来自同一个事前定义的尺度算子

合格含义优先为：五个相邻父级极值由**同一个多尺度表示中的同一尺度层**产生；或由一个事前冻结、可审计的自动尺度选择规则判为同一特征尺度。

禁止把“同一 K 线周期”“同一个 1% 反转阈值”“都落在 12—48 根”直接等价为同尺度。

### 1.3 父级必须真的吞掉更细结构

一个有意义的父级算子至少应表现出：随尺度增大，部分细尺度极值消失/合并，而较粗结构存活。v0.4.4 的关键失败指标 `collapsed_local_pivot_count` 中位数为 0，因此新方法必须直接检验“粗化是否真的发生”，不能仅用候选数量下降伪装成功。

### 1.4 因果性是定义的一部分，不是部署阶段再补

必须保存：

- 结构/极值发生时刻；
- 极值确认时刻；
- 两个完整周期完成确认时刻；
- 分类产生时刻；
- 有效信息时钟；
- 算法滤波延迟与额外确认延迟。

允许**明确且有界的确认延迟**；不允许未来数据回填历史事件。

### 1.5 分类层暂不改

这一轮只比较“父级波形表示/候选构造”。v0.4.3 的资格层、D1 range/trend 分类、信息时钟和互斥发布原则继续冻结。2018-06-20 的 `inefficient_leg`、case_10 与主视图 range=0 属于以后独立实验。

## 2. 从 v0.4.4 失败反推数学算子必须具备什么性质

本轮把算法能力拆成八项，而不是按论文名气排序：

1. **多尺度性**：存在有序尺度族，而非单一绝对周期门槛。
2. **真正粗化**：尺度增大时细极值应被抑制/合并，不应无约束产生新的伪结构。
3. **局部时间定位**：知道结构何时存在、何时消失，而不仅是全样本频谱。
4. **同尺度身份**：两个完整周期可以被明确归属于同一尺度。
5. **非平稳适配**：周期、振幅、漂移可随时间变化。
6. **时间因果/可递推**：可以逐根更新，不读取未来。
7. **前缀稳定**：追加未来数据不能改写已确认历史；最多改变明确标记的 provisional tail。
8. **可审计复杂度**：尺度、延迟、边界处理、参数必须在结果前冻结，不允许按 case 或收益挑选。

## 3. 跨学科候选方法预分析

### 3.1 Time-causal scale-space：升为第一生产候选

**来源领域：计算机视觉、信号处理、数学尺度空间。**

Lindeberg 的 time-causal temporal scale-space 用级联的一阶积分器/截断指数核建立因果、可递推的时间尺度空间。关键理论性质与本项目异常贴合：在一维时间信号上，相应 variation-diminishing 核随尺度增大保证**不会新增局部极值或零交叉**；同时论文给出时间因果尺度选择理论，使特征尺度反映底层结构的时间范围。

这恰好对应 v0.4.4 的根因：我们真正需要的不是“达到 12 根就晋升”，而是“增大尺度时微摆先消失、较大结构继续存活”。

**金融映射：**

- 原价格 `x(t)` 经过一组事前冻结的因果尺度层得到 `L(t; s)`；
- 每个尺度 `s` 上独立确认交替极值；
- `L0-H1-L1-H2-L2` 若来自同一 `s`，天然具有同尺度身份；
- 更细尺度的内部极值在更粗 `s` 被抑制，可直接记录父级吞并关系；
- 两个周期完成后再交给冻结的资格/D1，不把滤波角度直接当趋势。

**主要风险：**

- 因果滤波必然引入相位/时间延迟；必须把延迟显式作为结果，而不能事后对齐回填；
- 尺度选择本身不能从 case_00 事后挑“最像人眼”的层；
- 输入若直接用原价格，强单调趋势可能没有完整反转，这是允许的；若将来使用去趋势分量，漂移估计必须另做因果合同。

**预判角色：P0 / 首要生产候选。**

主参考：

- Tony Lindeberg, *Temporal Scale Selection in Time-Causal Scale Space*, Journal of Mathematical Imaging and Vision 58, 57–101 (2017), DOI: https://doi.org/10.1007/s10851-016-0691-3

### 3.2 Trailing / causal SSA：第二生产候选

**来源领域：非线性动力系统、地球物理、时间序列分析。**

SSA 通过延迟嵌入矩阵的奇异结构，把短而噪声的序列分成趋势、振荡和噪声成分。Vautard、Yiou、Ghil 明确把识别 oscillatory components 作为 SSA 的核心用途之一。

它非常适合检验 case_00 的另一种解释：表面上的 6/11/5/14 等局部摆动，是否只是一个较低频振荡成分上的高频扰动，而不是多个平级父浪。

**金融映射：**

- 只使用 trailing window 构造当前时刻 SSA；
- 只允许在当前边缘产生新状态，不允许每次窗口滑动后重写窗口内部既有确认事件；
- 从成对特征根/重构分量中提取振荡分量，再在该分量上确认两个完整周期；
- 窗口长度只属于计算支持域，不得被偷换成父浪绝对长度。

**主要风险：**

- 标准离线 SSA 的重构往往会随着窗口/样本增加改变历史 RC；若直接把全窗口重构当在线结果，会违反 prefix invariance；
- 分组 eigentriples 本身存在选择问题，可能变成新的事后“挑漂亮频率”；
- SSA 的“模态”不天然给出父子极值的单调粗化偏序，因此层级解释弱于 scale-space。

**预判角色：P1 / 生产候选，但必须通过 trailing-edge + prefix-stability 版本。**

主参考：

- Robert Vautard, Pascal Yiou, Michael Ghil, *Singular-spectrum analysis: A toolkit for short, noisy chaotic signals*, Physica D 58, 95–126 (1992), DOI: https://doi.org/10.1016/0167-2789(92)90103-T

### 3.3 事前固定的 causal wavelet / filter bank：第三生产候选

**来源领域：通信、信号处理、时频分析。**

Wavelet 的强项是同时具有尺度和时间定位，可以直接回答“某个尺度的振荡在什么时候存在”。它比全局 Fourier 更适合金融非平稳结构。

**金融映射：**

- 事前固定一组尺度/频带，使用严格单边、因果滤波器实现；
- 每个尺度输出一个可审计的带限/平滑分量；
- 在同一尺度分量上找五个交替、已确认极值，从而定义两个完整同尺度周期；
- 把群延迟/相位延迟计入确认时钟。

**主要风险：**

- 常见 CWT、对称 wavelet 或零相位滤波是双边的，直接用于历史图形会偷看未来；
- 频带边界若按 case 调整，会复制 v0.4.4 的参数问题；
- 带通信号的 extrema 可能受滤波 ringing 影响，必须做跳变/脉冲合成测试。

Daubechies、Lu、Wu 的 synchrosqueezed wavelet transform 给出了比 EMD 更严格的模态分离理论，但标准实现不自动满足本项目的在线因果合同，因此本轮把 SST 放到离线 oracle，而不是生产候选。

主参考：

- Ingrid Daubechies, Jianfeng Lu, Hau-Tieng Wu, *Synchrosqueezed Wavelet Transforms: An Empirical Mode Decomposition-Like Tool*, Applied and Computational Harmonic Analysis 30(2), 243–261 (2011), DOI: https://doi.org/10.1016/j.acha.2010.08.002

### 3.4 Topological persistence：层级语义高度匹配，但先做 reference/oracle

**来源领域：计算拓扑、计算几何。**

Persistent topology 用“一个特征在 filtration 中存活多久”区分 feature 与 noise。对一维价格曲线，局部极值的 persistence/prominence 提供了一种**相对重要性层级**：小摆动应先被消除，大摆动更持久；这比“13 根算父级、11 根算子级”更接近本项目需要的相对尺度。

Edelsbrunner、Letscher、Zomorodian 的经典工作把 persistence 明确定义为 filtration 中特征的生命周期；Cohen-Steiner、Edelsbrunner、Harer 又证明 persistence diagram 对小扰动具有稳定性。

**为什么暂不直接晋级生产候选：**标准 persistence 配对往往以完整函数/更大范围为对象，某个当前极值最终与谁配对可能依赖未来更深/更高的极值。除非先证明一个 streaming/prefix-native 版本不会回写已确认配对，否则它只能作为“什么结构相对持久”的离线层级参照。

主参考：

- Herbert Edelsbrunner, David Letscher, Afra Zomorodian, *Topological Persistence and Simplification*, Discrete & Computational Geometry 28, 511–533 (2002), DOI: https://doi.org/10.1007/s00454-002-2885-2
- David Cohen-Steiner, Herbert Edelsbrunner, John Harer, *Stability of Persistence Diagrams*, Discrete & Computational Geometry 37, 103–120 (2007), DOI: https://doi.org/10.1007/s00454-006-1276-5

### 3.5 EMD / HHT / EEMD：保留为自适应模态 oracle，不直接作为第一生产方案

Huang 等人的 EMD/HHT 专门针对非线性、非平稳数据，把复杂信号分成 IMF，并用 Hilbert 分析瞬时频率。它与“不同尺度波动叠加”的金融直觉高度一致，所以值得保留。

但它有两个对本项目很关键的风险：

1. **mode mixing**：相近/间歇频率可能进入同一个 IMF 或一个物理成分被拆散；EEMD 用加噪集成来缓解这一点，但引入额外随机/集成复杂度；
2. **端点效应与重绘**：sifting 的包络依赖极值及端点处理，追加未来数据可能改变尾部甚至更早的 IMF。离线 IMF 很漂亮，不代表在 t 时刻就能得到相同结果。

因此 EMD/EEMD 本轮的正确用法是：作为“自适应模态分解能否看见目标父结构”的离线 oracle，与因果方法比较；只有独立证明 causal/prefix-stable 版本后才有资格晋级。

主参考：

- Norden E. Huang et al., *The empirical mode decomposition and the Hilbert spectrum for nonlinear and non-stationary time series analysis*, Proceedings of the Royal Society A 454, 903–995 (1998), DOI: https://doi.org/10.1098/rspa.1998.0193
- Zhaohua Wu, Norden E. Huang, *Ensemble Empirical Mode Decomposition: A Noise-Assisted Data Analysis Method*, Advances in Adaptive Data Analysis (2009), DOI: https://doi.org/10.1142/S1793536909000047

### 3.6 VMD / SST：模态分离参考，不作为首轮在线实现

VMD、SST 的价值是提供更规则的模态/时频分解参照，帮助判断“EMD 看到的东西是不是算法特有”。但标准 VMD/SST 通常以一段完整窗口/变换为计算对象，首轮若直接用于在线识别，很容易把全窗口/未来信息混入历史结构。

本轮定位：**offline oracle / sensitivity reference**。除非之后独立冻结严格 trailing、不可回写版本，否则不参与生产晋级排名。

### 3.7 Directional Change：保留控制组，不再承担父级定义

Directional Change 的事件时间思想比固定 K 线窗口更接近市场路径事件，但它仍依赖价格阈值；阈值事件本身不提供“相对于内部微摆的父级层次”。因此它可以继续作为 event-driven control，回答“只改事件时间是否已经足够”，但不能再默认等价于父波形构造器。

### 3.8 Change Point Detection：只做状态切换辅助

Change-point 方法擅长回答统计机制/参数是否在某处发生变化；它不能独立产生 `L0-H1-L1-H2-L2` 两个完整同尺度波。因此只在未来父结构已经成立后辅助解释 regime transition，不进入本轮候选构造主赛道。

## 4. 方法筛选矩阵（结果前）

| 方法 | 同尺度两完整浪语义 | 真正层级粗化 | 原生/可实现因果 | 前缀重绘风险 | 本轮角色 |
|---|---|---|---|---|---|
| Time-causal scale-space | 高 | **高** | **原生** | 低（需计延迟） | **P0 主候选** |
| Trailing/causal SSA | 中高 | 中 | 可实现 | 中高 | **P1 主候选** |
| Causal wavelet/filter bank | 高 | 中高 | 可实现 | 中 | **P1 主候选** |
| Topological persistence | 高（相对显著性） | **高** | 待证明 | 高 | hierarchy oracle |
| EMD/EEMD/HHT | 高（模态） | 中高 | 非原生 | **高** | offline oracle |
| SST/VMD | 高（模态） | 中高 | 非原生 | 高 | offline oracle |
| Directional Change | 中 | 低 | 原生 | 低 | control |
| Change Point | 低 | 低 | 可实现 | 视算法 | auxiliary |

这张表是**数学/信息合同筛选**，不是数据结果。任何 P0/P1 方法都可能在 POC 中被否定；若全部失败，应全部拒绝，而不是选“相对最好”的一个强行升级。

## 5. 本轮最重要的结构性选择

### 5.1 不再要求“算法先找 v0.4.3 局部 pivot，再拼父级”

v0.4.4 的输入冻结局部极值是当时的单组件控制，但如果父级数学表示本身就是多尺度滤波/尺度空间，那么强行先经过 v0.4.3 ZigZag 局部 pivot 会把错误表示锁死。

因此 v0.5 预研究允许：**父级候选直接从原价格的事前冻结因果多尺度算子产生。**

为了保持可比较性，v0.4.3 局部极值仍作为 audit overlay：记录某个新父级周期内部吸收了多少 v0.4.3 局部极值/周期，但不再要求新父级只能由它们重组。

这是表示层变化，不是资格层/D1变化。

### 5.2 “12—48”退回它应有的位置

既有 `12—48` 只能继续作为**目标周期资格/诊断带**，用于说明一个候选最终落在哪个时间范围；它不参与：

- 什么时候关闭父级周期；
- 哪个细极值应被吞掉；
- 哪个尺度被选中。

### 5.3 先比较表示能力，再比较分类

第一轮 POC 只回答：

1. 是否能产生两个相邻、完整、同尺度周期；
2. 是否真的吞掉微摆，而不是删除整个对象；
3. 是否因果、前缀稳定；
4. 五个原生 5m 偏移边界是否更稳定；
5. 旧安全反例是否不复活；
6. 确认延迟是否可接受并被如实记录。

只有表示层通过后，才把候选送入冻结资格和 D1。

## 6. 首轮 POC 晋级顺序（冻结）

### 主赛道 A：Time-causal scale-space

优先验证“随尺度增加，case_00 那类微极值是否被系统吞并而不产生新伪极值”。这是与 v0.4.4 失败机制最直接的一一对应。

### 主赛道 B：Trailing/causal SSA

验证“局部碎片是否可以解释为低频父振荡 + 高频扰动”，同时严格做 prefix replay；若历史 RC 随窗口推进重绘，则直接降级为 oracle。

### 主赛道 C：Causal wavelet/filter bank

验证事前固定多分辨率频带能否产生稳定同尺度五点；必须报告滤波群延迟和 jump/ringing 反例。

### 参照赛道

- Persistence：相对显著性/父子层级 oracle；
- EMD/EEMD、SST/VMD：离线模态 oracle；
- Directional Change：阈值事件控制组；
- Change Point：暂不参与候选构造排名。

## 7. 本轮明确不做什么

- 不按收益、第三浪命中率或交易表现选数学方法；
- 不重新下载数据，不新增 2021+，不重采样新 K 线；
- 不为 case_00 手选尺度、频带、窗口或最对称五点；
- 不把离线 EMD/VMD/SST 图形回填成实时识别；
- 不调 v0.4.3 资格硬阈值；
- 不改 D1；
- 不把覆盖率变化当准确率；
- 不合并 main；PR #1 保持 Draft。

## 8. 预研究结论

**原先“EMD/SSA/Wavelet/DC/Change Point 五路并行”需要修正，而不是机械执行。**

从金融需求和 v0.4.4 失败机制倒推，最应该先验证的是一个具备“随尺度增加不新增细极值、而是逐步吸收微摆”性质的**因果尺度空间**。SSA 和 causal wavelet 是有价值的独立竞争路线；EMD/EEMD、VMD/SST、persistence 仍非常重要，但在未证明在线前缀稳定前只作为 oracle/reference。

这不是降低跨学科搜索范围，恰恰相反：**当前最强候选来自计算机视觉/尺度空间理论，而不是金融学。**

下一文件 `two_wave_multiscale_poc_protocol_v050.md` 冻结首轮实证 POC 的数据、合成反例、因果重放、评价量和停止规则。在该协议提交之前，不写任何 v0.5 检测器实现。
