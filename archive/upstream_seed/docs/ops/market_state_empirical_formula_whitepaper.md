# 市场状态择时经验公式基础设施白皮书

## 1. 为什么需要第三类知识资产

Feature/Factor Library保存可计算、可物化、可治理的因子。市场状态属性—工具基础设施
保存K线属性、工具公式、参数响应和相对能力证据。两者都不适合保存一种常见研究产物：
已经能写成数学关系、已有支持和反证、可能指导下一轮设计，但还不是因子也没有路由权
的“经验公式”。

因此新增轻量注册层：

```text
Factor/Feature                   -> 可物化输入资产
K线属性—工具/参数关系             -> 工具机制证据
Timing Empirical Formula         -> 有界经验关系、反例和候选用途
```

注册层不吸收行情，不重复因子库，也不把多个独立脚本塞成假通用文件。通用的只是知识
合同；每条经验公式保留自己的公式、证据、适用范围和验证脚本。

## 2. 第一条公式：短周期跨尺度相对换手凹坑

设基准频段为`b`，目标频段为`t>b`。只观察目标频段判断为上涨的K线。目标在自己的
上涨桶内恒为持有，基准可能持有或空仓。定义：

```text
T_i = 1(S_target,i-1 > threshold)
B_i = 1(S_base,i-1 > threshold)
D_i = 1(T_i=1 and B_i=0)
r_i = log(Open_{i+1}/Open_i)
```

毛方向价值为：

```text
G_b(t) = -sum(D_i * r_i)
```

当基准空仓后市场下跌，该项为正；当市场继续上涨，该项为负。定义同一目标上涨桶内的
相对额外成本：

```text
C_b(t) = cost(base within target_up) - cost(target within target_up)
```

成本乘数为`m`时，净相对价值、失败集合和成本盈亏平衡点分别是：

```text
F_b(t,m)=G_b(t)-mC_b(t)
I_b(m)={t>b:F_b(t,m)<=0}
m_star(b,t)=G_b(t)/C_b(t), C_b(t)>0
```

这是一条逐对会计恒等式，不是拟合公式。

## 3. 为什么是凹坑，不是单向手续费曲线

离散凹坑判据是：

```text
exists t1<t2<t3:
F_b(t1)>0 and F_b(t2)<=0 and F_b(t3)>0
```

它的左、中、右三段分别可能由不同主矛盾支配：

1. **近端共享转向**：S5与S10都可能频繁换手，但它们共享许多转向；绝对成本高不等于
   相对额外成本高，所以近端可以仍为正。
2. **中段相对换手扩张**：目标慢线开始过滤小反复，基准仍切换，`C_b(t)`快速上升；
   同时`G_b(t)`可能尚小甚至为负，净值落入凹坑。
3. **远端毛价值接管**：相对额外成本趋于饱和。如果慢背景内部包含更大回撤，基准快速
   转空的避跌价值增加，`G_b(t)`超过`C_b(t)`，净值再次转正。

因此“手续费造成失败”只解释了部分中段。147组频段对审计中，开发期有17对是毛方向
为正但被成本吃掉，另有17对毛方向本身已负；前向期对应为12对和21对。方向关系型
失败去掉手续费也不会恢复。

## 4. 同口径机制见证

S5作为基准、共同滞回`0.20`、买1/卖6基点、2014—2017前向切片：

| 目标上涨桶 | 毛方向价值 | 相对额外成本 | 净相对价值 |
|---|---:|---:|---:|
| S10 | +0.092694 | 0.049300 | +0.043394 |
| S15 | -0.070621 | 0.063500 | -0.134121 |
| S20 | +0.008866 | 0.067500 | -0.058634 |
| S25 | +0.251170 | 0.065200 | +0.185970 |
| S30 | +0.331186 | 0.065100 | +0.266086 |

这张表回答了“S10绝对换手更高，为什么反而不落坑”：从S10到S20，相对额外成本
从0.0493增到0.0675；到S25/S30不再增加，毛方向价值却明显上升，于是净值右转。

但它只是一张**机制见证**。同一`0.20`切片在2009—2013训练期不是相同凹坑；零滞回
主口径里S10也为负。因此不能选择`0.20`并宣称规律已经跨期稳定，更不能把S15/S20
直接写成生产路由。

## 5. 可迁移内核与不可迁移表象

可迁移的内核是：

- 对每个基准频段独立计算`G`、`C`、`F`；
- 只在同口径目标上涨桶比较；
- 用`F`的符号和稳定性定位失败集合；
- 分开标注换手成本型与方向关系型失败；
- 通过压力面观察凹坑边界是否移动。

不可迁移的表象是：

- S5必然在S15—S20失败；
- 任意频段都有一个凹坑；
- 目标周期固定等于基准的2倍、2.5倍或5倍；
- 观察到一张U形表就可以选择阈值。

在当前147对测试域内，严格“单一失败前缀”开发期为6/14、前向期3/14、两段共同只有
S10和S20。按周期比值拟合的交界约2.14倍；缩小到S60以下约2.56倍，但两者前向分类
准确率都低于简单的全部预测胜出基线。这是否决固定倍数公式的关键反证。

## 6. 候选组合增强

用户提出的增强可写成职责分配：

```text
if stable_failure_pair(b,t) and target_up:
    owner = target_scale
else:
    owner = base_scale
```

等价地：

```text
target_up            -> target_scale
target_flat_or_down  -> base_scale
```

它的经济含义是：目标频段只接管自己有相对优势的上涨桶；基准保留更擅长快速避跌的
横盘/下跌桶。这是从经验公式推导出的最小候选路由，不等于已证明超额。后续验证必须
将“找失败频段”和“验证组合路由”分开，避免同样本选择与评价。

## 7. 权限、Schema和渐进式披露

机器合同为`market_state_empirical_formula_registry@1.0`，每个条目必须携带：公式、
判据、适用边界、观察切片、候选用途、限制、证据引用、中文字段和四类权限。当前固定：

```text
factor_registration_authority=false
dynamic_parameter_authority=false
tool_routing_authority=false
production_authority=false
```

注册表构建读取行情0行、收益0行；它不重新研究，只确定性发布已审计知识。

渐进式披露链固定为：

```text
ai-readme.md
  -> README.md / docs/00-index.md
  -> docs/user/README.md / docs/ops/README.md
  -> docs/user/market_state_foundation_workflow.md
  -> docs/user/market_state_empirical_formula_workflow.md
  -> 本白皮书
  -> source / schema / scripts / tests / 原始证据
```

## 8. 五位一体验收

- 文档：`docs/user/market_state_empirical_formula_workflow.md`
- 白皮书：本文件
- 当前机器快照：`docs/ops/evidence/market_state_empirical_formula_registry@1.0.json`
- 代码：`src/factor_lab/market_state/empirical_formula_registry.py`
- 测试：`tests/unit/test_market_state_empirical_formula_registry.py`
- 工作流：构建与验证脚本及上述渐进式索引

验收命令：

```bash
PYTHONPATH=src pytest -q tests/unit/test_market_state_empirical_formula_registry.py
ruff check src/factor_lab/market_state/empirical_formula_registry.py \
  scripts/build_market_state_empirical_formula_registry.py \
  scripts/validate_market_state_empirical_formula_registry.py \
  tests/unit/test_market_state_empirical_formula_registry.py
```
