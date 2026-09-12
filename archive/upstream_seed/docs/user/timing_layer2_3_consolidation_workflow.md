# 择时基础设施 Layer 2/3 使用工作流

## 入口

机器注册表：`docs/ops/timing_layer2_3_registry@1.0.json`  
Python facade：`factor_lab.market_state.timing_layer2_3_contracts`

Layer 2 的使用顺序固定为先测量：

```python
from factor_lab.market_state.timing_layer2_3_contracts import (
    build_layer2_volatility_measurements,
)

measurements = build_layer2_volatility_measurements(bars)
```

返回面只含连续量与时序身份；没有未来评价目标、三态、认领或仓位。需要三态时，
由 3b 的独立 adapter 显式消费测量面：

```python
from factor_lab.market_state.timing_layer2_3_contracts import (
    build_layer3b_volatility_states,
)

states = build_layer3b_volatility_states(measurements)
```

`states` 仍只是时效状态标签，不是仓位；3b 可被更完整 Layer 2 测量取代，不是
长期底座。

六轴与论文核也通过独立 Layer 2 adapter 暴露：

```python
from factor_lab.market_state.timing_layer2_3_contracts import (
    build_layer2_paper_kernel_measurements,
    build_layer2_six_axis_measurements,
)
```

3a 不提供策略选择 API。现役身份固定为十五工具表 `tool_registry_v1_5` 和评价平台
`@4.0`；工具相对耦合、论文核第十四工具身份和公式倒推只属于词汇/考卷/结构
合同。

## 验证

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/unit/test_timing_layer2_measurement_boundary.py \
  tests/unit/test_timing_layer3_strategy_boundary.py \
  tests/unit/test_market_state_timing_priority_composition.py
```

本工作流不授予策略、参数、生产或新鲜样本外权限。
