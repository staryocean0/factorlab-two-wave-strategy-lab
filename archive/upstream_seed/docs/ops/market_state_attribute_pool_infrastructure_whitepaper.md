# 市场状态属性池基础设施白皮书

状态：V1 framework implemented / first catalog published

## 1. 目标

项目过去已经拥有K线属性、带通波动率矩阵、论文核时序和多种专项诊断，但它们
分散在不同output/artifact/evidence目录，身份和更新责任不统一。本设施不重算
这些科学结果，而是在其上建立可持续更新的治理层：

- 五池固定身份；
- 五位一体入口；
- 声明式source registry；
- 文件级哈希与血缘；
- 内容寻址snapshot；
- fail-closed更新和current指针。

## 2. 为什么不能只有一个大宽表

五类数据的维度不同：

```text
核心K线属性：carrier × view × timestamp/year × attribute
频谱时序：carrier × view × timestamp × band × measurement
论文核响应：carrier × view × timestamp × span × normalization
载体关系：carrier_a × carrier_b × view × horizon × measurement
衍生品执行：underlying × contract/expiry × strike/moneyness × timestamp × measurement
```

强塞进同一宽表会制造空列、重复值和错误权限。本设施统一“管理”，不统一成
同一物理schema。

## 3. 五位一体合同

文档解释怎么找；白皮书定义为什么和边界；代码执行注册、哈希与发布；测试锁定
失败关闭；工作流负责随时间更新。缺任一项，池状态不得升为ready。

机器注册表按固定顺序声明五池，禁止临时增加第六个匿名池。新池必须先升级
registry schema和五位一体表面。

## 4. Snapshot与不可变性

更新器读取声明source，计算文件SHA-256和语义digest，生成：

```text
artifacts/market_state/attribute_pool_infrastructure_v1/
  current.json
  snapshots/snapshot-<semantic_digest>/
    catalog.json
    manifest.json
    pools/<pool_id>.json
```

snapshot id由registry与source bytes决定。同样输入重复运行命中同一snapshot；
旧snapshot不覆盖。`current.json`只是小型指针文档，不是数据本体。

新增源不得修改已冻结注册表身份。`apply_registry_overlays()`接受失败关闭的加法型overlay，在内存中解析完整注册表后发布新snapshot。当前MO Theta overlay将十一档成本表接入衍生品执行池；overlay不能新增pool、重复source_id或开启策略/路由/生产权限。

## 5. Source治理

source registry必须声明：`source_id/path/role/format/required/authority`，可选声明
source schema和说明。required源缺失立即失败；optional源缺失进入catalog缺口，
不得静默消失。

本设施不移动、删除或改写source。历史source hash漂移时产生新snapshot；封存
证据仍绑定旧bytes或Git历史blob。

## 6. 池状态

| 状态 | 含义 |
|---|---|
| `framework_ready` | 框架已建，尚未统一登记数据 |
| `ready` | 注册required源齐全，机器合同可消费 |
| `partial` | 已有数据可消费，但载体/时间/指标覆盖不完整 |
| `planned` | 只有身份与缺口，没有可消费数据 |
| `blocked` | 更新因外部源或合同错误阻断 |

状态只描述基础设施，不证明alpha、收益或生产可用性。

## 7. 五池边界

- 核心池不保存完整band矩阵、论文核收益或衍生品字段。
- 频谱池允许从K线源派生，但必须独立manifest和频带坐标。
- 论文核池的`paper_kernel_daily_gross_return_s*`是工具响应，不是普通自相关。
- 载体关系池必须保留两端载体身份，不能回写单载体属性。
- 衍生品执行池不得把杠杆解释成零成本。

## 8. 更新验收

1. 五位一体文件存在；
2. 五池id和顺序精确；
3. 权限全部fail closed；
4. required source存在且哈希可读；
5. snapshot制品哈希通过；
6.同输入semantic digest稳定；
7. 旧snapshot和source未覆盖；
8. current指针指向完整snapshot。
9. validate-current重新计算全部已登记source哈希；源先更新而未publish时立即失效。
10. current钉死snapshot manifest SHA-256，catalog同时重算自身semantic digest。

操作入口见[更新工作流](../user/market_state_attribute_pool_update_workflow.md)。

## 9. 当前物化与汇聚状态

当前snapshot `snapshot-cf04e70b87e62dfd`登记85个source；除既有衍生品执行绑定外，已通过加法overlay登记Layer 2 V2及状态机降权前回迁的连续研究材料：

| 池 | 状态 | source数 | 当前边界 |
|---|---|---:|---|
| 核心K线属性 | ready | 11 | 纯56列、98载体—视图对、1204年度行已物化；新增未来Provider和DataHub 2m/3m/10m/20m固定快照绑定，粗路径仍关闭 |
| 多频段谱系 | partial | 11 | 7×14年度band/邻频/聚合长表已统一；逐棒时序与严格因果相位仍未形成 |
| 论文核响应 | partial | 18 | 新增七载体14:00日级S1/S5/S10响应5项产物；完整16尺度×7×14扩展仍未完成 |
| 载体关系 | partial | 2 | 已形成7载体×14视图的年度21对关系；逐棒严格因果滚动状态待补 |
| 衍生品执行 | partial | 27 | V1.4父池 + MO Theta + CSI1000 router/成本子链 + 连续BBO历史适配/价差测量 + Provider预注册 + G2A时序测量面板/G2B-P开发无证据状态 + MO连续BBO/L1 OFI/有界一档执行 + ETF期权费率/乘数合同；G1/G3停止，G4与ETF期权盘口等待 |

各池由独立物化脚本生成受测产物；catalog发布仍只登记身份、哈希和血缘，不移动
或复制任一池的源文件。
