# 六轴与工具专属因子统一基础设施工作流

> 四层拆分：六轴公共市场状态属于 Layer 2；工具相对耦合属于 Layer 3a。
> 两者通过独立合同身份消费同一来源，不共享认领、仓位或生产权限。

> 版本：1.0
>
> 状态：`measurement_authority=true`，信号/路由/动态参数/生产权限全部为 `false`
>
> 入口文档（渐进式披露的第一站）；深度细节请读对应白皮书与冻结子系统工作流。

## 这是什么

把两套已有但尚未统一的项目级基础设施收敛为一个公开查询入口：

1. **六轴严格因果市场状态**——方向、方向记忆、波动水平、波动记忆、路径与尾部、截面共振；
2. **工具公式—参数—机制—因子映射**——覆盖当前 14 个现役工具。

统一入口只做**薄编排与已登记因子的严格因果物化**：复用而不复制 `timing_six_axis.py`、`tool_formula_mechanisms.py`、`tool_registry_v1_4.py`。现役工具身份以 `tool_registry_v1_5` 为准，但本入口不把 LAT 六桶方法回填进冻结 R2F 包。构建会读取封存边界内的日线行情来生成质量回执，但不做有效性研究，也不授予任何信号或路由权限。

## 三层信息模型

```
原始严格因果市场数据
  → 公共市场状态层（六轴标题 + 多尺度分量/期限结构）
  → 工具公式与参数层（14 工具，direct / geometry_only / validity_only / cost_only）
  → 工具相对耦合层（无量纲匹配量）
  → 完整性/可用性/研究权限门
  → 下游工具查询、参数曲面、工具 Battle 和 M/F/R 归因
```

- `common_market_state`：六轴标题只是**监控投影**，不是任何工具调参的充分统计量；下游应读多尺度分量。
- `tool_relative_coupling`：由工具真实公式倒推，将公共状态与工具内部决策量联系；优先无量纲量。
- `execution_constraint`：成本、执行延迟、最短持有、T+1/下一棒执行等约束。

## 完整性 vs 有效性

**"完整"指每个因子都有机器可读结局**（defined/materializable/materialized/blocked_missing_input），**不等于"验证有效"**。

因子权限梯度严格分离：

- 有公式定义 ≠ 能计算；
- 能计算 ≠ 已经物化；
- 已物化 ≠ 实证有效；
- 实证有效 ≠ 有路由/动态参数权；
- 有研究权 ≠ 有生产权。

本轮所有因子的 `signal_authority / routing_authority / dynamic_parameter_authority / production_authority` 全部为 `false`。

## 怎么用：三条命令

> 命令须从项目根目录运行，并用 `PYTHONPATH=src` 让 `factor_lab` 包可被导入（与项目其它脚本一致）。

### 1. 构建

```bash
PYTHONPATH=src python scripts/build_market_state_unified_timing_infrastructure.py \
  --output-dir output/market-state-foundation/unified-timing-infrastructure/current
```

构建会读取默认日线 OHLC（`output/baylum-data-update/current/cloudridge_1d_qfq_service_confirmed_*.csv`，与六轴同源）物化可计算的专属因子；可用 `--price-path` 指定其它日线文件。当前物化回执**只覆盖 `1d` 载体**，不得把该回执外推为 `60m/15m` 已实现。历史不足以让任一声明为已物化的因子产生有效值时，构建直接失败，不以零或全空列冒充成功。

产物（`current/`）：

- `manifest.json`——包清单、冻结子系统引用摘要与每个产物的 SHA256；
- `factor_catalog.json`——三层因子统一目录（物化后已回填真实 materialization_status）；
- `tool_factor_coupling.json`——14 工具→公式→参数→机制→因子耦合；
- `tool_parameter_formula_registry.json`——14 工具×参数×公式×信号相关性注册表；
- `factor_topology.json`——exact_alias / same_root / proxy_family 拓扑；
- `factor_timeseries.csv`——12 个可物化因子的严格因果时序（截止 2020-12-31，不打开 2021—2026）；
- `factor_timeseries_manifest.json`——时序质量回执、来源文件 SHA256、真实载体频率，以及逐因子的首个/末个有效时点和非空覆盖；
- `completeness_matrix.csv`——每个因子的完整性结局矩阵；
- `validation_report.json`——前缀不变证据、来源血缘、13 缺失量结局账本；
- `report_zh.md`——中文报告。

### 2. 验证

```bash
PYTHONPATH=src python scripts/validate_market_state_unified_timing_infrastructure.py \
  --output-dir output/market-state-foundation/unified-timing-infrastructure/current
```

复核三个 JSON Schema、语义摘要、**manifest 中每个产物的 SHA256（篡改即失败）**、14/14 工具对账、冻结前缀不变、exact-alias/同根不重复计票、参数信号相关性审计与权限门。

### 3. 查询（四个视角）

```bash
# 某个工具需要哪些公共轴、专属因子、参数与时序可用性
PYTHONPATH=src python scripts/query_market_state_unified_timing_infrastructure.py --tool <tool_id>

# 某个因子的公式、时钟、代理家族、消费工具/参数与证据地位
PYTHONPATH=src python scripts/query_market_state_unified_timing_infrastructure.py --factor <factor_id>

# 某个参数是否直接改变信号、影响哪个公式量、需要哪些因子
PYTHONPATH=src python scripts/query_market_state_unified_timing_infrastructure.py --parameter <tool_id>:<param_id>

# 所有未物化、缺输入或仅待验证项
PYTHONPATH=src python scripts/query_market_state_unified_timing_infrastructure.py --missing-only

# 只返回某时点已可用的因果事实（--as-of 做真实因果过滤）
PYTHONPATH=src python scripts/query_market_state_unified_timing_infrastructure.py --tool <tool_id> --as-of 2010-06-30
```

每个视角返回自包含 JSON，不需要跨多份报告人工拼接。`--as-of <YYYY-MM-DD>` 按**每个因子自己的首个/末个有效时点**过滤；预热期尚未形成该因子、或请求日已经超出物化数据尾端时，均不会把它报告为可用。

## 不可破坏的边界

1. 旧 13 工具 R2F 前缀、失败注册表、C1.2/C1.3 证据、六轴当前包**字节不变**；本包只引用不改写。
2. 第 14 工具 `paper_kernel_multiscale_trend_router` 是 **append-only 扩展**，不回填旧 C1.2 关系包，不伪造历史 R2 验证结论；历史 `causal_jump_gap_shock` 不得恢复为第 15 工具。
3. `path_efficiency_wN == abs(direction_wbi_wN)` 是精确别名，**禁止重复计票**；ACF/VR/论文核/Hurst/BDCI 属同根投影，相关较低不得自动升格为正交。
4. 一切时序严格因果；截面轴缺失时保持缺失，不用云脊自身填充。
5. `geometry_only / validity_only / cost_only` 参数**不进入当前信号调参自由度**，只有 `direct` 参数才是调参候选。
6. 2021—2026 继续封存；本轮不做因子有效性/参数规律/工具路由/收益验证。

## 下游实证的唯一公共前提门

本入口完成因子、工具、参数和时序的完整性对账后，动态参数或工具路由
研究不得直接进入回测。必须先进入
[动态参数稳定性优先与因子失败归因工作流](market_state_dynamic_parameter_reliability_workflow.md)，
以“载体正交 + 大幅绝对/相对失败极端相关”筛选候选因子，并拒绝事后全样本最优静态基线；
随后进入
[四类择时策略普适前提门工作流](market_state_timing_strategy_prerequisite_workflow.md)，
按串联+并联DAG执行：身份时钟、结构可控性、决策可识别性、在线相对信息和时间可用性
构成五个硬前提；机制归因与属性补全在可识别性后并联研究，不误杀未解释候选。
未解释或高容量候选必须在嵌套样本外层提供升级证据；硬门失败仍关闭主链。
关闭当前主链后不得只输出“失败”：必须调用前提门2.1的三类恢复合同，给出回退层、必做/禁做动作和判死范围，并用关联新run继续。

## 与深度入口的关系

本工作流是统一入口；需要子系统的公式/机制/六轴细节时，仍读各自的深度工作流：

- 六轴：`docs/user/market_state_timing_six_axis_workflow.md`
- 工具公式机制：`docs/user/market_state_tool_formula_mechanism_workflow.md`
- 基础设施：`docs/user/market_state_foundation_workflow.md`
- 动态参数/工具路由前提门：`docs/user/market_state_timing_strategy_prerequisite_workflow.md`

白皮书（设计理由、同根压票、权限梯度、负面研究继承）：`docs/ops/market_state_unified_timing_factor_infrastructure_whitepaper.md`。
