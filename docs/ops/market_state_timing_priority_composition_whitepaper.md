# 择时策略组合优先级基础设施白皮书

> 四层归属：Layer 3b 时效原型。当前空瀑布合同为 `@1.1`，只把合法工具白名单
> 对齐 `tool_registry_v1_5`；历史十四工具 `@1.0` 保留。该层可被更完整 Layer 2
> 测量取代，不是长期底座，`production_authority=false`。

## 决策

项目新增一个策略中立的择时工具组合层。它复用同一套工具身份、状态输出和证据，
分别形成上涨捕获与下跌防护的责任瀑布，从而避免 Risk-Off 与滤波择时重复开发
互为正反面的信号。

## 工具注册决策

当前表命名为 `tool_registry_v1_5`，直接继承冻结的 V1.4 十四工具前缀，只追加
LAT 通道 `lowpass_bandpass_lat_channel`。V1.4 已经把论文核多尺度趋势登记为
第十四工具。没有基于 V1.3 继续追加，因为 V1.3 的跳变工具独立路由责任已经撤销。
历史登记仍可追溯，但不能借版本递增重新获得现役责任。

第十四工具将论文原式的十二尺度因果 EWMA 方向信息组织成 slow/middle/fast
层次状态。第十五工具是 LAT 通道：P64 一阶因果低通中轨 + 带通残差宽度，
注册对照仍是无缝 k=1.5；做空对照仍是 `width_k1p0` / k=1.0。六桶相对高频是
研究方法，不是新的注册表行。注册表只证明身份完整、公式合同存在、基准可执行。

## 组合数学

对方向 `s` 和有序工具 `T1...Tn`：

```text
R0(s) = eligible universe
Ck(s) = R(k-1,s) ∩ E(Tk,s)
Rk(s) = R(k-1,s) \ Ck(s)
```

`Ck` 是第 k 层独占责任桶，`Rk` 是交给下一层的剩余桶。该形式具有三个重要性质：

1. 同侧责任桶互斥，便于独立分桶回测和归因；
2. 工具只对自己真正擅长的状态负责，不必用调参硬吃全部行情；
3. 改一层时可同时看到它抢走了哪些K线、给后层留下了哪些K线。

上涨捕获和下跌防护使用两条独立瀑布。跨侧冲突如何转成最终仓位属于未来组合
策略合同，不在本框架中偷做决定。

## 为什么本轮不排具体顺序

“先挑走K线”会改变所有后层工具的样本分布。因此单工具全市场收益不能直接用来
排序；必须比较它在候选状态中的责任价值、前层认领造成的机会成本、剩余桶对后层
的影响，以及训练外稳定性。本轮没有为排序读取任何收益行，避免用未经归因的历史
高收益提前锁定架构。

## 工程合同

- 当前注册表实现：`src/factor_lab/market_state/tool_registry_v1_5.py`
- V1.4 前缀仍冻结：`src/factor_lab/market_state/tool_registry_v1_4.py`
- 组合实现：`src/factor_lab/market_state/timing_priority_composition.py`
- 构建脚本：`scripts/build_market_state_tool_registry_v1_5.py`
- 框架脚本：`scripts/build_market_state_timing_priority_composition.py`
- 测试：`tests/unit/test_market_state_tool_registry_v1_5.py`、
  `tests/unit/test_market_state_timing_priority_composition.py`

组合层仍强制检查同侧唯一优先级、完全一致的K线索引、布尔且无缺失
的认领条件。未认领K线保持 `unassigned`，不存在隐式默认策略。
现役白名单以 V1.5 十五工具为准；V1.4 十四工具前缀保持冻结。

## 权限

当前只是基础设施骨架：`production_authority=false`、
`dynamic_parameter_authority=false`、`tool_routing_authority=false`。
后续具体优先级必须以独立版本、冻结搜索范围、分桶评价、图形归因和时间外验证
进入，不能直接改写本空框架快照。

首个增量版本见[三层双向择时策略路由白皮书](market_state_timing_strategy_routing_whitepaper.md)：
它固定责任位顺序和方向—仓位分离合同。最新 V3 只锁定第一层的暴跌反弹与
P48→P96双向真通道；第二、第三层继续保持空负责人。本 V1 空快照仍只作骨架历史入口。
