# 云脊论文原式EWMA核多尺度基础设施唯一入口

> 四层拆分：本文只承接 Layer 2 的 16 尺度时序测量；第十四工具身份属于
> Layer 3a 的 `tool_registry_v1_5` 前缀。本文不做路由样板或选参。

> 权威状态：`current`
>
> 面向对象：项目内部AI、外部AI、人工研究者
>
> 边界：这是K线收益过程属性的研究基础设施，不是任一个择时工具的实际收益，不授予路由、调参或生产权限。

本文是该基础设施的**唯一渐进式入口**。从 `ai-readme.md`、属性总文档、Schema索引或证据文档进入时，最终都应回到本文确认阅读层级和权限边界。

## 第0层：理论源头（最高优先级）

1. [原论文 PDF](../../research_materials/05_trend_following_momentum/sepp_lucic_2026_science_practice_trend_following.pdf)
2. [原论文中文精读摘要](../../research_materials/05_trend_following_momentum/sepp_lucic_2026_chinese_summary.md)
3. [论文对云脊13工具体系的历史影响评估](../../research_materials/08_project_notes_assessments/cloudridge_13_tool_implications_assessment_20260801.md)
4. [云脊截止2020年的论文原式历史验证](../ops/evidence/cloudridge_trend_following_paper_validation_20260801.md)

原论文是公式与经济含义的理论源头。中文摘要用于快速定位，项目影响评估用于理解13工具的关系，历史验证用于了解早期同样本归因与样本外反例。

但要注意：历史验证的 `5/10/21/63/125/250/500`七尺度、截止2020年数据和20bp论文比较成本都不是当前16尺度属性面。当前机器数据权威从第2层读取。

## 第1层：项目权威解释

- [多尺度白皮书](../ops/cloudridge_paper_kernel_multiscale_timeseries_whitepaper.md)：公式、概率分布、2009—2026中枢/振幅报告、短尺度与长尺度结论及权限边界。
- [CloudRidge K线属性总入口](cloudridge_attribute_infrastructure.md)：该属性与BDCI、BCI、WBI、lag memory等其他K线属性的并列关系。
- [CloudRidge K线属性基础设施白皮书](../ops/cloudridge_attribute_infrastructure_whitepaper.md)：公共属性字典和产物边界。

## 第2层：当前权威数据与统计报告

完整历史权威目录（下次获准重建时按1.2合同产出）：

```text
output/market-state-foundation/paper-kernel-multiscale-timeseries/current/
```

由于当前2021年以后数据仍处于研究封闭状态，本轮没有覆盖该目录中已有的1.1全历史制品。已落地且可直接消费的1.2真实数据是截止2020年的封闭前快照：

```text
output/market-state-foundation/paper-kernel-multiscale-timeseries/through-20201231-v1.2/
  paper_kernel_multiscale_timeseries.csv
  manifest.json
```

该快照包含2,911个逐日点、16个尺度，时间从2009-01-14至2020-12-31，`sealed_2021_plus_rows_read=0`。旧 `current/` 不得被误称为1.2制品，直到封闭规则允许重建。

| 文件 | 用途 |
|---|---|
| `paper_kernel_multiscale_timeseries.csv` | 16尺度权威逐日宽表；原始值列为 `paper_kernel_daily_gross_return_s{span}`。 |
| `paper_kernel_span_summary.csv` | 全历史均值、正值概率、分位数、偏度、峰度、零轴中心和尾部形状。 |
| `paper_kernel_annual_summary.csv` | 2009—2026每个自然年、每个尺度的不重叠年度毛收益摘要。 |
| `paper_kernel_scale_regime_summary.csv` | 16尺度的前后期中枢、振幅比、分阶段均值和路径形状。 |
| `report_zh.md` | 人读十六尺度统计报告，同时覆盖1—60日和100—500日。 |
| `validation.json` | 公式、统计口径、中文字段、因子ID、渐进索引和权限的机器合同。 |
| `manifest.json` | 全部制品哈希。 |

固定尺度为：

```text
1, 2, 3, 4, 5, 10, 15, 20, 30, 60, 100, 150, 200, 300, 400, 500
```

1—4日是对原12尺度的向下补齐，使用完全相同的论文原式、一日严格滞后和250日一次性预热。其中 `s=1` 时 `nu=0`，信号退化为前一日标准化收益，仍然是有定义且可因果使用的原公式特例。详细数值以上述CSV为准；新增四条本身不授权任何参数选择。

## 两套并行波动率标准化数据面

原 `1.2` 数据面继续保留，所有尺度统一使用前一日已经完成的33日EWMA波动率。这是论文原式入口，不改名、不改值、不被新版本覆盖。

项目另提供一套**同周期波动率标准化**研究面：S5用5日波动率、S10用10日波动率，依此类推。其截至2020年的封闭数据目录为：

```text
output/market-state-foundation/paper-kernel-matched-volatility-timeseries/through-20201231-v1.0/
  paper_kernel_matched_volatility_timeseries.csv
  normalization_choice_catalog.csv
  normalization_comparison_summary.csv
  validation.json
  report_zh.md
  manifest.json
```

同周期版本对每个尺度 `s` 使用：

```text
sigma[s,t-1] = lag1(sqrt(EWMA_s(r[t]^2)))
z[s,t]       = r[t] / sigma[s,t-1]
f[s,t]       = 0.15/sqrt(260) * S[s,t-1] * z[s,t]
```

两版都严格因果、都保留250日一次性预热。区别只在标准化分母：原版固定33日，新版与信号周期相同。外部AI应先读 `normalization_choice_catalog.csv`，明确声明使用 `fixed_33_day_lagged_ewma_volatility` 或 `matched_span_lagged_ewma_volatility`，不得把两种模式的字段当成同一条线。

同周期版没有加波动率下限、截断或Winsorize。尤其S1的分母等同于前一日单日波动：前一日接近不动而下一日明显波动时，标准化值会非常大。这是原始定义的真实风险；“提供选择”不等于“推荐S1实盘使用”。详细风险和逐尺度对照见[同周期波动率版本说明](../ops/cloudridge_paper_kernel_matched_volatility_timeseries_whitepaper.md)。

## 第3层：标准化选择与参数面研究资产

下列内容是本基础设施对下游研究提供的可复用证据，不是独立策略或策略版本：

- [三责任桶短波动率标准化工作流](market_state_paper_kernel_three_bucket_volatility_v1_workflow.md)：在冻结 V3 高斜率下跌、高斜率上涨和暴跌反弹责任掩码内，对 `S1–S5 × raw/2/3/4/33日波动率` 做固定时钟 Battle 与90%参数面审计。
- [三责任桶短波动率标准化白皮书](../ops/market_state_paper_kernel_three_bucket_volatility_v1_whitepaper.md)：保存稳定规律、失败结论、反例和后续消费边界。

它们必须从本页渐进披露，不得在“策略族入口”中被注册为新策略。其参数面可供 RLR/RIR 或其他组合研究消费，但不因被某个策略消费而改变基础设施资产身份。

## 第4层：机器合同、代码和测试

- Schema：[`cloudridge_paper_kernel_multiscale_timeseries@1.2.json`](../schemas/json/cloudridge_paper_kernel_multiscale_timeseries@1.2.json)
- 唯一公式内核：`src/factor_lab/cloudridge/paper_kernel.py`
- 时序/统计/报告生成器：`src/factor_lab/market_state/paper_kernel_multiscale_timeseries.py`
- 运行入口：`scripts/run_cloudridge_paper_kernel_multiscale_timeseries.py`
- 独立校验入口：`scripts/validate_cloudridge_paper_kernel_multiscale_timeseries.py`
- 公式与回归测试：`tests/unit/test_market_state_paper_kernel_multiscale_timeseries.py`
- 属性字典集成测试：`tests/unit/test_cloudridge_attribute_infrastructure.py`
- 同周期波动率生成器：`src/factor_lab/market_state/paper_kernel_matched_volatility_timeseries.py`
- 同周期波动率Schema：[`cloudridge_paper_kernel_matched_volatility_timeseries@1.0.json`](../schemas/json/cloudridge_paper_kernel_matched_volatility_timeseries@1.0.json)
- 同周期波动率运行入口：`scripts/run_cloudridge_paper_kernel_matched_volatility_timeseries.py`
- 同周期波动率独立校验：`scripts/validate_cloudridge_paper_kernel_matched_volatility_timeseries.py`
- 三责任桶参数面Schema：[`market_state_paper_kernel_three_bucket_volatility@1.0.json`](../schemas/json/market_state_paper_kernel_three_bucket_volatility@1.0.json)
- 三责任桶参数面内核：`src/factor_lab/market_state/paper_kernel_three_bucket_volatility_v1.py`
- 三责任桶参数面独立校验：`scripts/validate_market_state_paper_kernel_three_bucket_volatility_v1.py`

## 执行

```bash
PYTHONPATH=src python scripts/run_cloudridge_paper_kernel_multiscale_timeseries.py
PYTHONPATH=src python scripts/validate_cloudridge_paper_kernel_multiscale_timeseries.py
PYTHONPATH=src python scripts/run_cloudridge_paper_kernel_matched_volatility_timeseries.py
PYTHONPATH=src python scripts/validate_cloudridge_paper_kernel_matched_volatility_timeseries.py
PYTHONPATH=src python scripts/run_market_state_paper_kernel_three_bucket_volatility_v1.py
PYTHONPATH=src python scripts/validate_market_state_paper_kernel_three_bucket_volatility_v1.py
```

前两条命令生成并校验原固定33日版本；中间两条生成并校验截至2020年的同周期波动率并行版本；最后两条生成并校验三责任桶的75格参数面研究资产。三组生成器都校验来源哈希、语义digest和全部制品哈希，互不覆盖。

## 时间与统计口径

- 信号严格滞后一日；`decision_eligible_timestamp`指明日点最早的下一交易日可用时点。
- 最初250个日线只在整条历史起点预热一次，不是滚动测量尺。
- 年度值是自然年内原始日点均值乘260；年度区间不重叠。
- 振幅比为 `std(2018—2025年度值)/std(2009—2017年度值)`。
- 分阶段均值为该阶段全部原始日点均值乘260。
- 年度、阶段和分布统计都是描述性报告，不会写回原始因子，不是第二估计窗。
- 2026统计是截至当前数据日的年内未完整值。

## 外部AI禁止事项

- 不得为原始点再减局部均值乘积；
- 不得引入240/245/250日滚动测量尺；
- 不得把单日正负翻译为趋势/反转路由；
- 不得把论文连续线性核收益当成第14工具的实际策略收益；
- 不得把论文中的“回看周期取决于持续性与成本”改写成本基础设施已授权动态调参；
- 不得从逐笔盈亏反向优化该内核。
- 不得把同周期版本伪称为论文唯一原式；它是项目并行研究选项。
- 不得省略所用标准化模式，也不得在没有单独验证时把S1极端值静默截断。
- 不得把三责任桶参数面资产注册成独立策略；它对 RLR/RIR 只提供基础设施证据，不提供策略身份或生产权。

## 验收

```bash
PYTHONPATH=src pytest -q \
  tests/unit/test_market_state_paper_kernel_multiscale_timeseries.py \
  tests/unit/test_cloudridge_attribute_infrastructure.py \
  tests/unit/test_documentation_consistency.py

ruff check \
  src/factor_lab/cloudridge/paper_kernel.py \
  src/factor_lab/market_state/paper_kernel_multiscale_timeseries.py \
  scripts/run_cloudridge_paper_kernel_multiscale_timeseries.py \
  scripts/validate_cloudridge_paper_kernel_multiscale_timeseries.py
```

必须同时通过：16尺度逐点公式一致、前缀不变、1日公式特例、原12尺度逐点不变、5日正确结果对账、概率分布和阶段统计口径、原论文/摘要/白皮书/Schema/代码/测试的渐进索引、来源与制品哈希，以及旧错误入口零残留。
