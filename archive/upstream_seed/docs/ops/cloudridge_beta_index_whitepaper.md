# 云脊A股Beta指数白皮书

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `cloudridge_beta_index_reference`。
> 第 1 层只引用该载体，不改指数算法、成分或权重。本层不是造 bar；墙上时钟见 [`timing_layer1_datahub_clock_split_whitepaper.md`](timing_layer1_datahub_clock_split_whitepaper.md)。

日期：2026-05-21
状态：权威方法口径
范围：云脊A股Beta指数 / CN-A CloudRidge Beta Index 的数学公式、产品边界、资产准入、等权归一化和渲染口径。

运行命令、历史导出、GPU/CPU 参数与 runtime collection 迁移见 [市场相关性 Beta 强度云指数运行手册](market_cloudridge_beta_index_runbook.md)。TopK 相关性核心指数见 [市场相关性核心指数白皮书](market_correlation_core_index_whitepaper.md)。

---

## 1. 产品定义

固定名称：

```text
中文名：云脊A股Beta指数
English: CN-A CloudRidge Beta Index
Symbol: CN_A_CLOUDRIDGE_BETA_EQW
```

“云脊”指市场 beta 云的脊线：它衡量全市场股票共同运动的主导骨架，不是交易建议，也不是市值加权基准。

当前产品链路为：

```text
DataHub full-market A-share PIT daily bars
  -> close-to-close returns
  -> full-market Pearson correlation matrix
  -> per-stock average Fisher-z correlation strength
  -> Dominant Beta Strength Cloud left-shoulder selection
  -> equal-weight / price-neutral constituent pool
  -> weekly or daily rolling levels
  -> linear/log K-line rendering
```

---

## 2. 一等市场资产准入

`CN_A_CLOUDRIDGE_BETA_EQW` 是自建指数，但它仍然是标准化市场价格/点位序列。若导出为 OHLC/level 行，必须带有：

```text
asset_id/symbol = CN_A_CLOUDRIDGE_BETA_EQW
asset_kind      = self_built_index
source_family   = price_volume
timestamp/asof/available_at
open/high/low/close/volume
```

source-universe 准入仍严格约束来源：自建指数和自建组合只有在底层数据来自标准化市场 universe 时才可进入因子计算，通常为 `price_volume`。它们不是引入分析师预期、新闻/NLP、事件 alpha 或另类数据的后门。一旦准入，Factor DSL 和标准 price-volume 计算会像处理其他资产行一样处理它们。

---

## 3. 权威选择公式

先决条件：

- 常规 PIT/live dataset 使用 `available_at <= as_of_date`。
- 历史回填若 `available_at` 是入库时间戳，可使用 `availability_mode=trading_day`，表示日线 bar 在其交易日可见。
- eligible asset 必须满足 `min_periods=max(60, ceil(0.8 * lookback))`，除非测试显式覆盖。
- 绝对股价永远不是权重输入。

对于 rebalance/as-of date `D`，只使用不晚于 `D` 可用、且位于 lookback 窗口内的数据。对每个 eligible stock `i`，计算其收益与每个有效其他股票 `j` 的 Pearson 相关系数：

```text
rho_ij = corr(return_i, return_j)
z_ij = arctanh(clip(rho_ij, -0.999999, 0.999999))
b_i = mean_j(z_ij)
s_i = tanh(b_i)
```

`b_i` 是股票在 Fisher-z 尺度上的全市场 beta-strength score。使用 Fisher-z 是因为相关系数有界，且在 -1/+1 附近非线性；在 z-space 中求平均能得到更稳定的全市场强度坐标。`s_i` 是为了展示而转换回相关性尺度的值。

每日 beta cloud 是所有 `b_i` 的截面分布：

```text
mu_z = mean_i(b_i)
sigma_z = std_i(b_i)
left_shoulder_z = mu_z - sigma_z
selected_pool = { i | b_i >= left_shoulder_z }
```

白话解释：把股票从最强的全市场共振到最弱排序，取分布完整右侧，并在弱相关尾部开始变平的左肩处停止。这对应“从右至左，右肩全取，到了左侧下降斜率变缓点”的语义。

`coverage_floor` 是安全护栏，不是主公式。如果离散左肩切分选出的股票少于配置下限，则将切分点放宽到满足下限的最小排名。rebalance 记录同时保存公式点 `strength_left_shoulder_z` 和用于复现成分的有效 cutoff 字段。

---

## 4. 指数点位与归一化

指数 level 口径必须保持**收益等权、价格中性**：

```text
daily_return(D) = mean(return_i(D) for all selected constituents with valid returns)
level(D) = level(D-1) * (1 + daily_return(D))
```

股票绝对价格绝不会作为权重使用。10 元股票和 1000 元股票在同一成分池中权重相同；每只股票只通过百分比涨跌幅进入和退出指数。若某只成分股当天缺少有效收益，其余有收益的成分股按等权重新归一，并在 level 诊断中记录缺失名单。

周度导出从每个周度生效日开始，直到下一周度生效日前，延续同一套成分股和等权收益规则。一次 rebalance 固定该周 constituents；每条 daily level 行都是当天有效 selected constituent returns 的等权平均。

---

## 5. 生效时点与无未来函数

`as_of_date=D` 的调仓只使用不晚于 `D` 可得的数据；成分股在之后的 `effective_date` 生效，通常是从行数据推断出的下一交易日。除非显式 `force=true`，否则同一个 `index_id + as_of_date` 重跑应保持幂等。

---

## 6. 已移除口径

以下口径已不再属于生产选择器：

- graph connected-component / 最大连通池；
- threshold grid / 渗流跃迁峰；
- marginal coverage peak / right-shoulder 旧字段；
- soft cap 或固定手动 cutoff；
- legacy `correlation_threshold_pool_index_*` 作为新写入 collection。

旧字段只允许作为历史 runtime 读取或迁移 fallback；新 payload 和公开控制面必须使用 CloudRidge 命名与 beta-strength-cloud 公式。

---

## 7. 渲染与后端

渲染规则：K 线报告默认使用线性 y 轴；多年视图可用 `price_scale=log` / CLI `--price-scale log` 渲染。对数刻度只改变展示，不改变指数点位。

计算后端：CPU 与可选 CuPy/ROCm GPU 后端必须计算相同的 PIT 收益矩阵、Pearson 相关性、Fisher-z 行均值和左肩选择。`compute_backend=auto` 可以回退 CPU；`compute_backend=cupy` 必须在 CuPy/GPU 不可用时快速失败，避免静默降级。运行诊断应记录 `compute_backend`、`gpu_acceleration` 和可见设备数量。
