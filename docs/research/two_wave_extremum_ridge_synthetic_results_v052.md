# v0.5.2 TCSS Extremum Trajectory / Exact-Ridge Tuple：合成硬门正式结果

日期：2026-09-05

状态：`synthetic_parent_identity_pass_real_data_not_yet_tested`

操作基线仍为 **v0.4.3**。本结果仅说明 v0.5.2 的 extremum-level ridge identity / exact-ridge tuple birth 在结果前冻结的合成测试中成立；**不代表真实中证1000 morphology 已通过，不升级 recognizer，不激活 qualification/D1/H1/H2。**

## 1. 结果前协议与唯一改动

预研究：`docs/research/two_wave_extremum_ridge_preanalysis_v052.md`

冻结协议：`docs/research/two_wave_extremum_ridge_protocol_v052.md`

v0.5.1 已正式否定的跨尺度原子是 five-extrema sliding candidate window。v0.5.2 只把跨尺度原子改成**单个 confirmed TCSS extremum**：

`TCSS extrema nodes -> adjacent-scale causal ridge IDs -> ridge deaths -> exact five-ridge tuple birth -> frozen raw projection -> frozen v0.4.3 qualification/D1/ledger`

未加入 persistence threshold、未用真实 case 反推 matching distance gate、未使用 12–48 选层级、未改 raw projection、qualification 或 D1。

## 2. 最终正式 synthetic run

- 实现/测试 HEAD：`a67909f61a7b3d02bf6f4b5b586a7aacc91566df`
- GitHub Actions：**run `33971793744` success**
- 全量 pytest：**387 tests，0 failures**
- artifact：`9971147234`
- artifact SHA256：`e454ed36cfd23e917630c4114dd3daecea2b94741c5d4b3ad219016208c8fdb4`
- artifact size：24,131 bytes
- expires：2026-10-05

## 3. 合成硬门通过了什么

### S0 严格单调 raw price

严格上涨和严格下跌序列均：

- 0 parent tuple births
- 0 evaluated raw two-wave
- 0 selected

因此 TCSS/ridge 简化不能在没有原价格实际反转时凭空造两个 raw reversal waves。

### S1 单 extremum 的跨尺度 immutable identity

手工构造 fine `parent -> child -> parent` 同 phase extrema，coarse 只保留两个 parent：

- 两个 surviving parent coarse nodes 继承原 parent ridge IDs；
- 中间 child ridge 只在后一个 coarse continuation 已确认时发布 scale death；
- prefix 只含第一个 coarse node 时，第一个 continuation 与 full run 完全相同；
- future coarse information 不回头重分配该 ancestor。

### S2 exact five-ridge tuple birth

手工构造五个 parent ridges，中间插入两个 child ridges：

- finer scale 五个 parent ridge IDs 不是连续五点；
- child ridges death 后，同样五个 parent ridge IDs 在 coarse scale 首次成为连续五点；
- exact tuple birth 成功产生；
- 删除 child-death 证据后，同一个 parent birth 不再成立。

因此 birth 是 topology/adjacency change，而不是“coarse scale 又出现一个看起来相近的五点窗口”。

### S3 多组 nested parent + child waves

结果前固定三组 parent period / child period / child amplitude ratio：

- `(80,16,0.30)`
- `(96,24,0.25)`
- `(64,16,0.40)`

三组均产生由 internal child ridge death 支持的 parent tuple births；tuple ID 全程由 exact ordered ridge IDs 定义，同一 tuple_id 的成员没有 sliding replacement。

正常 nested-wave 合成信号中 lineage anomaly 没有成为常态机制。

### S4 chirp prefix replay

频率连续变化并叠加额外局部频率的 chirp 上，full run 与 25%/50%/75% prefix 对所有已经确认的：

- ridge nodes / ridge IDs
- continuation edges
- ridge deaths
- tuple IDs / tuple births

逐字段一致。

这说明首轮 ridge identity 至少在合成非固定周期下满足 prefix-native 要求。

### S5 jump + small oscillation

最终安全语义是：**单个 jump 不得参与制造一个通过资格/发布的 parent two-wave**，而不是错误要求整条序列没有任何合法波。

合成序列 jump 前后本身存在真实 period-13 小振荡，因此它们可以形成普通局部 range 对象；但所有跨越 jump 的 evaluated parent 均：

- `scale_qualified = false`
- 包含 `jump_dominated_leg`
- 0 crossing selected

说明 frozen v0.4.3 raw jump gate 在该合成反例上仍起作用。

## 4. 两次失败为什么必须保留

### 第一次失败：ledger 字段兼容 bug

首次专用 workflow `33971511410` 中，ridge/tuple 数学门已通过，但 chirp end-to-end 与 jump end-to-end 在复用冻结 v0.5.1 `CharacteristicExclusiveLedger` 时失败：v0.5.2 记录使用 `birth_scale_level`，ledger 仍读取 `characteristic_scale_level`。

修复仅增加三个值完全相同的兼容 alias：

- `characteristic_scale_level = birth_scale_level`
- `characteristic_scale_id = birth_scale_id`
- `characteristic_sigma_bars = birth_sigma_bars`

没有改变 ridge matching、tuple birth、raw projection、qualification 或 D1。

### 第二次失败：jump 测试反例语义写错

第二次 workflow `33971669126` 仅失败于原断言 `run.ledger.selected == []`。

失败记录实际是 `[55..81]`、`[107..133]` 等完全发生在 jump=450 之前的真实 period-13 小振荡，并没有利用 jump。要求整条含真实振荡的序列 0 selected 会把合法波也当错误。

因此只修正**测试问题**：现在要求必须存在 crossing raw candidates，并验证所有 crossing candidate 被 `jump_dominated_leg` 拒绝且 0 crossing selected。算法与资格阈值均未修改。

这两次失败作为研究审计链保留，不能用最终绿灯覆盖。

## 5. 当前可以下什么结论

可以保留的结论只有：

> **把跨尺度 identity 从 sliding five-point window 下沉到 single-extremum ridge，并以 internal child-ridge death 触发 exact five-ridge tuple birth，在合成层解决了 v0.5.1 的“成员滑移”定义问题，且通过 prefix/monotonic/jump 安全硬门。**

不能下的结论：

- 不能说 CSI1000 的 parent waves 已正确识别；
- 不能说 case_00 已修复；
- 不能说 offset 稳定性改善；
- 不能升级 v0.4.3；
- 不能激活 qualification/D1 修改；
- 不能进入 H1/H2、收益或交易。

## 6. 下一安全步骤

现在才允许写**六视图真实数据 runner / formal workflow**，规则必须严格复用冻结协议，不增加新 case 或参数。

正式真实数据应输出：

1. 每层 extremum nodes / ridge nodes / exact tuple 数；
2. ridge continuation edges、deaths、lineage anomalies；
3. tuple births 及 birth-level 分布；
4. internal child-death 数量与 parent tuple 吞掉的 v0.4.3 micro extrema；
5. raw projection valid/invalid 及原因；
6. frozen qualification / D1 / disjoint ledger；
7. 六视图 18 次 exact prefix replay；
8. 五个 native 5m offset publication IoU；
9. 既有 case_00/02/10/11/14 与 2018/2019/2020 固定窗口审计。

若真实数据 parent identity 明显改善、但健康 parent 被 frozen qualification 拒绝，可判 `parent_identity_pass_qualification_pending` 并重新激活资格单组件研究。

若 exact-ridge identity 仍不能把 v0.5.0 已存在的 parent coarse structure 稳定送入 candidate layer，则 TCSS hierarchy 路线停止继续深挖，转 trailing SSA / causal wavelet competitive POC。
