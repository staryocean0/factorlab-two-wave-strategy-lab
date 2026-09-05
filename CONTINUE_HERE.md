# 两浪研究继续入口：v0.5 多尺度数学表示预研究已冻结，操作基线仍为 v0.4.3（2026-09-05）

## 当前研究状态

v0.4.4 的“绝对周期带直接定义父级”假说已经正式否定；当前没有新基线。**操作研究基线继续是 v0.4.3**，状态仍为 `morphology_replication_not_yet_accepted`。

本轮已经按用户新增约束启动 v0.5 预研究：数学工具必须先证明其表示语义、因果性和层级性质确实对应金融需求，不能因为离线分解图形漂亮就进入实现。

优先阅读：

- [v0.5 跨学科数学预研究](docs/research/two_wave_multiscale_pre_research_v050.md)
- [v0.5 结果前 POC 冻结协议](docs/research/two_wave_multiscale_poc_protocol_v050.md)
- [v0.4.4 正式结果与否定结论](docs/research/two_wave_hierarchy_results_v044.md)
- [v0.4.3 正式结果与失败归因](docs/research/two_wave_confirmation_ablation_results_v043.md)
- [此前 D0/D1 完整结果](docs/research/two_wave_same_scale_results_20260905.md)
- [旧 C1/H16/W128 历史入口](CONTINUE_HERE_C1_H16_W128_ARCHIVE.md)

## 金融需求没有改变

首轮生产语义继续冻结为 **raw-price reversal wave**：

- 低点起算：`L0 -> H1 -> L1 -> H2 -> L2`；高点起算对称；
- 两个完整周期共享中间同相位端点；
- 五个父级极值必须属于同一个可审计尺度；
- 如果 `x(t)=bt+A sin(ωt)` 且 `b>Aω` 使原价格严格单调，则当前 raw-reversal 语义应输出 0 个完整两浪；残差/IMF/RC 中存在周期只能标为 `detrended_cycle_only`，不能偷偷换金融目标。

后续父状态仍是：在两个完整同尺度波形成立后，再依据整体漂移/包络几何区分震荡、上涨趋势、下跌趋势或不确定。当前不改资格层和 D1。

## 为什么 v0.5 允许直接从原价格建立多尺度父级表示

v0.4.4 的单组件控制曾要求父级只能重组 v0.4.3 已确认局部极值，但该实验已经证明：如果父级仍被旧局部切割表示锁死，大尺度结构会继续被合法的 13、16、17、19、25 根微周期切碎。

因此 v0.5 表示层允许使用**事前冻结、严格因果的多尺度算子直接作用于原价格**。v0.4.3 局部极值仍完整保留为 audit overlay，用于统计新父级到底吸收了多少旧局部微摆，但不再强制控制父级闭合。

这是表示层研究边界变化，不是资格/D1变化。

## 跨学科预筛选结论（结果前）

按“金融语义 -> 数学层级性质 -> 在线因果性 -> 前缀稳定性”的顺序筛选，而不是按论文名气：

1. **P0：Time-causal scale-space (TCSS)**。来源于尺度空间/计算机视觉/信号处理。最贴合 v0.4.4 根因：尺度增大时细极值应被系统抑制/合并，而不是第一次达到绝对根数就闭合父级；实现可递推、时间因果。
2. **P1：Trailing/causal SSA**。适合检验“局部碎片 = 低频父振荡 + 高频扰动”，但标准 SSA 重构有历史重绘风险；只能通过 trailing-edge + prefix-stability 版本争夺生产候选。
3. **P1：事前固定 causal wavelet/filter bank**。时间/尺度定位强，但禁止双边 CWT、零相位 `filtfilt` 和未来 padding；滤波延迟和 ringing 必须成为硬测试。
4. **Oracle/reference：Topological persistence、EMD/EEMD/HHT、SST/VMD**。这些方法对相对持久性/模态分解很有价值，但标准离线版本可能依赖未来端点或重写历史，在未证明 prefix-native 之前不能直接生成生产事件。
5. **Control：Directional Change**；**Auxiliary：Change Point Detection**。DC 仍依赖事件阈值，不天然建立父子层级；CPD 不独立产生两个完整波形。

没有“必须选一个赢家”的要求；如果主候选不能同时过金融语义、因果性、真实粗化和安全反例，可以全部否定。

## 已冻结的 v0.5 POC 硬门

不看收益，按词典序硬门比较：

1. 金融语义正确；
2. confirmed 历史 `prefix rewrite = 0`；
3. 有真实层级粗化，不能靠删除整个对象伪装；
4. case_02、case_11/14、jump synthetic 等安全反例不退化；
5. case_00 / 2018 / 2019 / 2020 固定窗口出现机制上可解释的改善；
6. 五个原生 5m 偏移边界稳定性；
7. 明确报告算子延迟、极值确认延迟和覆盖成本。

`12—48` 已退回目标周期资格/诊断带，**不允许用于父级闭合或尺度选择**。

## TCSS 第一条生产候选 POC 已启动

已新增：

- `src/factor_lab/visual_structure/two_wave/multiscale_v050.py`
- `tests/unit/test_two_wave_multiscale_v050.py`
- `scripts/run_two_wave_multiscale_tcss_poc.py`
- `scripts/run_two_wave_multiscale_tcss_poc_fast.py`（仅把 v0.4.3 lineage 区间计数从全扫描替换为 `searchsorted`，不改研究逻辑）
- `.github/workflows/two-wave-multiscale-tcss-poc.yml`

TCSS 使用事前冻结的 14 层半倍频程几何尺度格；尺度参数是**因果平滑核的标准差**，不是波浪长度，也不是 12—48 的变形。

合成硬门已经覆盖：

- 严格单调 raw price 不得凭空产生两浪；
- 父周期 + 高频子摆必须随尺度增加真正减少细极值，同时不能把父结构全部删光；
- 五个极值必须构成同一尺度的两个完整周期；
- 扩展未来样本后，已确认 scale-space / extrema / two-wave candidates 必须逐条保持不变。

通用 CI 已确认新增代码没有破坏旧工程：371 项测试通过。

正式六视图 TCSS real-data POC 通过专用 workflow 执行，要求：

- 主 `5m_offset_0` + 4 个原生 5m offset + `1m_official`；
- 14 个事前冻结尺度全部输出，**不根据 case_00 选择“最好看”尺度**；
- 六视图 × 25%/50%/75% = 18 次固定前缀重放；
- 主视图硬断言 v0.4.3 audit overlay 仍为 `4706候选 / 341资格 / 212互斥发布`；
- case_00/02/10/11/14 与 2018-06-20、2019-04-15、2020-07-15 全部逐尺度审计。

当前正式执行应以最新 `two-wave-multiscale-tcss-v050-poc` workflow 的最新 HEAD 为准；在其结果归档前，不宣称 TCSS 胜出，也不选择特征尺度。

## 下一安全停点

TCSS 全样本 POC 完成后，先回答两个问题，而不是直接写“v0.5 基线”：

1. TCSS 是否同时通过 raw-reversal 语义、零重绘和真实粗化？
2. 即使多个尺度能重构 case_00，是否存在**事前、因果、自动的 characteristic-scale / persistence 规则**，而不是事后挑尺度？

与此同时，tSSA 与 causal wavelet/filter-bank 的竞争路线必须按照已经冻结的语义分流和因果门独立验证，不能在看到 TCSS 结果后改规则。

如果 TCSS 只有“多尺度粗化”但没有合法的在线尺度选择，它最多晋级为表示候选，不是新基线；下一轮应先冻结 characteristic-scale 规则。

## 不变的授权和禁止项

只用仓库现有 2015—2020 development 行情，不新增、不重采样。主目标固定中证1000原生 `5m_offset_0`；其余四个原生5m偏移只做稳健性，1m仅诊断。

候选审计层可重叠，发布层必须互斥；未覆盖/未决/provisional 尾部不能伪装成震荡。计算确认和原数据 `available_at` 必须分开。

负向实验必须原样归档，不能为了得到正结果事后改协议。

**PR #1 继续 Draft，不合并 main。形态验收前不进入第三浪/H1/H2，不按收益选参，不计算/开放交易权限，不生产部署。**
