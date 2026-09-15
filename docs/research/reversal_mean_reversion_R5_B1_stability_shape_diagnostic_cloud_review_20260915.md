# R5-B1 stability/shape diagnostic — cloud review

日期：2026-09-15

Diagnostic identity：`R5_B1_stability_shape_diagnostic_v1`

Parent identity：`R5_multiscale_serial_dependence_state_v1`

正式裁决：`R5_B1_diagnostic_supported_for_specialist_research`

## 1. 执行与证据边界

本次 current cloud session 先重新核对长期研究分支 `codex/two-wave-phase1-20260905`。执行前实际 head 为 `cf8397c12a9defa243dc272224dedebe6ccd3251`，相对旧 handoff head 的新增提交只涉及 cloud binary bridge / ops 记录，没有改变 CL-008 frozen scientific protocol、runner 或 tests。

current cloud container 对 public GitHub binary 的直接获取仍受 DNS / UTF-8-only connector 路径限制；这不是数据不存在、样本不足或字段不足。

随后按仓库优先级切换到已授权 local execution surface。local temp clone 的 head 精确为 `cf8397c12a9defa243dc272224dedebe6ccd3251`，且冻结 artifacts 精确匹配：

- runner blob：`a5f1f4dea7fb46a6d42c7d91f3404b1ec8022f28`
- tests blob：`539b6bba9f76ebf00584a40b9483bd6c692c30b2`
- source size：`3,351,411 bytes`
- source SHA256：`bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`

因此本次真实 diagnostic execution surface 是 `authorized_local_machine`；current cloud session 的角色是重新核对冻结身份、审阅 receipt 并完成仓库裁决。不得把本次执行写成 current-cloud direct run。

## 2. Tests

在隔离 Python 3.11 venv 中执行 frozen test target：

```text
python -m pytest -q tests/unit/test_broad_rmr_R5_B1_stability_shape.py
```

结果：exit code 0，4/4 tests passed。

venv 只补齐 `pyproject.toml` 允许范围内的运行依赖；仓库 scientific artifacts 未修改。

## 3. Entry reproduction gate

CL-007 entry reproduction 全部通过，absolute tolerance = `1e-12`：

```text
TRAIN rows      = 41,685
VALIDATION rows = 21,428
B0 beta = [0.00556707839525621, 0.034874518817555246]
B1 beta = [0.00494714709230104, 0.013036096384464763, -1.0692286210370299]
B0 VALIDATION MSE = 1.011653266505294
B1 VALIDATION MSE = 1.0101116108135515
```

与 frozen CL-007 reference 的数值差异均在 `1e-12` 内。`entry_reproduction.pass = true`。

## 4. D1 — day breadth

固定 TRAIN-fit B0/B1，不 refit。

```text
VALIDATION pooled:
  days = 487
  fraction_B1_better = 0.5482546201
  median day improvement = +0.0003966155
  weighted MSE B0/B1 = 1.0116532665 / 1.0101116108

2019:
  days = 244
  fraction_B1_better = 0.5327868852
  median day improvement = +0.0003048387
  weighted MSE B0/B1 = 0.9986089092 / 0.9961336416

2020:
  days = 243
  fraction_B1_better = 0.5637860082
  median day improvement = +0.0004338087
  weighted MSE B0/B1 = 1.0247513043 / 1.0241471025
```

2019、2020 均满足 `fraction_B1_better > 0.50` 且 median improvement > 0。

`D1_day_breadth_supported = true`。

这说明 pooled 的约 0.15% 小增量不是只由少数极端日期机械撑起；但改善幅度仍然很小，不能升级为“策略成功”。

## 5. D2 — anti-persistence shape

TRAIN-fixed quintile edges：

```text
[-0.04447927493, -0.02649760937, -0.01334927487, 0.01049508362]
```

核心形状检查：

```text
VALIDATION pooled:
  bottom slope = +0.0904780318
  top slope    = -0.0024427426
  five-bin slope trend vs mean anti = -1.1071576768

2019:
  bottom slope = +0.1086742381
  top slope    = -0.0347971278
  trend = -1.6388676207

2020:
  bottom slope = +0.0642587007
  top slope    = +0.0246674685
  trend = -0.5119166844
```

VALIDATION pooled、2019、2020 三组都满足：

1. top quintile slope < bottom quintile slope；
2. five-bin slope-vs-mean-anti linear trend < 0。

`D2_shape_supported = true`。

注意：协议不要求五个 bins 严格逐点单调；2020 的中间 bins 有噪声并不违反 frozen gate。

## 6. 正式裁决

D1=true 且 D2=true，因此唯一允许的裁决是：

`R5_B1_diagnostic_supported_for_specialist_research`

含义仅为：这个很小的 B1 anti-persistence interaction 具有足够的日度广度和预注册机制形状，值得交给专门 research identity 做进一步稳定性、transport 和经济映射研究。

它不表示：

- fresh OOS 已通过；
- BLACKBOX 已分配或读取；
- mixed-state 已成为稳定 regime classifier；
- HMM/rSLDS/Koopman 已获授权；
- 已证明可交易 PnL / Sharpe；
- production / paper trading 已获授权。

## 7. Evidence hygiene

```text
TRAIN/VALIDATION reused = true
fresh_OOS_claim = false
BLACKBOX_read = false
post_2020_rows_read = false
PnL_read = false
production_authority = false
```

Receipt：`docs/research/local_broad_rmr_R5_B1_stability_shape_diagnostic_receipt_v1.json`

下一步只允许建立 specialist research handoff；BLACKBOX 继续保持 `none_assigned`。母仓同时恢复广而浅的独立方向发现职责，不把整个项目改造成 R5 专题仓。
