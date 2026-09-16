# R7 specialist Stage 1 inferential readiness — cloud review

日期：2026-09-16

Identity：`R7_specialist_stage1_inferential_readiness_v1`

Parent：`R7_native_1m_rejected_excursion_v1`

正式裁决：

`R7_specialist_stage1_inferentially_supported_calibration_drift`

## 1. 执行审计

第一次受控 run `35043104558` 在 synthetic tests 阶段停止，真实 Stage 1 runner 未执行。失败来自退化 synthetic residual regression 的理论 slope=0、cluster variance=0，但浮点最小二乘残留约 1e-20，导致零宽 CI 在机器精度上未字面包含 0。

该问题只做数值实现修正：CI closed-interval containment 使用 absolute tolerance `1e-12`。C1/C2/C3 定义、门槛和 adjudication table 均未修改；修正后在看任何真实 Stage 1 outcome 之前建立 execution-freeze v2。

有效执行：

- execution commit: `1fe920d11e27a8dd4578ef3bf7093272097f3eb1`
- GitHub Actions run: `35043298059`
- job: `104627633019`
- workflow conclusion: `success`
- frozen synthetic tests: `5/5 passed`
- artifact id: `10426421296`
- artifact digest: `sha256:3dfffac91504c8c479346a9b37e21c6b7636e13bc48a685e8f36e9d78ccd337c`
- entry reproduction: passed at `1e-12`
- BLACKBOX=false; post-2020=false; PnL=false; fresh OOS claim=false; production=false.

## 2. C1 — day-clustered coefficient uncertainty

`C1_clustered_coefficient_supported = true`

Trading-day CR1 95% CI：

| group | rejection beta | 95% CI | trading days |
|---|---:|---:|---:|
| TRAIN | -0.532770 | [-0.589459, -0.476080] | 973 |
| VALIDATION | -0.395450 | [-0.444995, -0.345906] | 487 |
| 2019 | -0.393841 | [-0.470222, -0.317461] | 244 |
| 2020 | -0.396962 | [-0.461036, -0.332887] | 243 |

四组 CI upper 均明显低于 0。R7 rejected-excursion 的负向增量不是由把 bar 当独立样本造成的假精度。

## 3. C2 — frozen prediction day robustness

`C2_day_prediction_robustness_supported = true`

使用 frozen TRAIN-fit B0/B1，不重新训练。

2019：

- days=244
- mean day improvement=`0.0236298`
- bootstrap 95% CI=`[0.0094331, 0.0375024]`
- median=`0.0167605`
- positive-day fraction=`61.07%`

2020：

- days=243
- mean day improvement=`0.0261273`
- bootstrap 95% CI=`[0.0133050, 0.0394150]`
- median=`0.0245927`
- positive-day fraction=`61.32%`

两年均通过预注册 gate。P10 仍为负，说明不是每天都改善；本结论是总体日级 breadth/uncertainty 支持，不应解释为逐日稳定获益。

## 4. C3 — fixed-coefficient calibration / residual sufficiency

`C3_calibration_clean = false`

VALIDATION pooled：

- calibration intercept=`0.01608`, CI 包含 0；
- calibration slope=`0.80744`, 95% CI=`[0.71494, 0.89993]`，不包含 1；
- B1 residual endpoint slope=`+0.03108`, CI=`[0.01316, 0.04899]`，不包含 0；
- B1 residual rejection slope=`+0.13732`, CI=`[0.08777, 0.18686]`，不包含 0。

2019 / 2020 分开后方向一致：

- calibration slope 分别 `0.81076 / 0.80430`，各自 CI 均低于 1；
- residual endpoint slope 均为正且 CI 不含 0；
- residual rejection slope 均约 `+0.139 / +0.136` 且 CI 不含 0。

因此 TRAIN-frozen B1 在 VALIDATION 上表现为系统性 over-amplitude / coefficient drift：机制方向仍成立，但固定 TRAIN 系数并非直接 transport-ready。

特别是 rejection：TRAIN beta约 `-0.533`，VALIDATION local beta约 `-0.395`；frozen 模型对 rejection 的负向幅度更强，留下正 residual-rejection slope。该解释与 calibration slope<1 和 2019/2020 一致。

## 5. 科学裁决与权限

C1=true、C2=true 说明 R7 机制在考虑 trading-day dependence 后仍有支持，且 frozen B1 的预测改善具有正的日级 breadth 和 bootstrap uncertainty 下界。

C3=false 表明不能把 2015–2018 的固定系数直接称为可迁移模型。

因此正式裁决必须是：

`R7_specialist_stage1_inferentially_supported_calibration_drift`

允许：

- 保留 R7 specialist mechanism；
- 设计一个新的、事前冻结的 calibration strategy research；
- 或在数据治理明确授权后做 mechanism transport，并把 coefficient transport 与 mechanism transport 分开评价。

不允许：

- 宣称 frozen coefficients transport-ready；
- 直接用 VALIDATION local re-fit 替换 TRAIN coefficients 再把改善称 OOS；
- outcome 后搜索滚动窗口、衰减系数、阈值、年份或方向；
- BLACKBOX/post-2020；
- PnL/Sharpe 反向选 calibration；
- complex-model rescue；
- paper trading / production。

Production authority=false。
