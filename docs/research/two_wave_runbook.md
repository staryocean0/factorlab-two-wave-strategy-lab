# 两浪识别研究使用说明

本版是第一阶段的可审查研究候选。已实现原始收盘反转、完整周期、两浪局部包络、分类、冻结边界首次越界、流式重放与独立标注。它不输出持仓，不管理同向越界之后的持仓反向退出，不执行第三浪统计或收益回测。

## 安装与复跑

使用 Python 3.11，在仓库根目录执行：

```bash
python -m pip install -e . editables==0.6
python scripts/validate_theme_package.py
python -m pytest -q
python scripts/run_two_wave_research.py --data 'data/development/*.parquet' --output cloud_results/two_wave_h0 --reversal-logs .008,.01,.012 --replay-bars 1200
python scripts/check_two_wave_stability.py --data 'data/development/*.parquet' --output cloud_results/two_wave_stability
python scripts/build_two_wave_synthetic_gallery.py
```

`editables` 是当前 Hatch 精确 editable 安装需要的运行依赖。原始 `pyproject.toml` 及冻结资产未修改。验证器需要仓库的全部 14 个 Parquet；部分文件下载环境下的验证失败不能称作全量通过。

`--data` 可重复传入一个或多个供应商视图路径或通配符。`--max-bars` 限制运行输入前缀，仅适合调试，输出记录实际输入范围。`--replay-bars` 只限制打包到交互图中的初始前缀，不改变完整识别统计；需要查看更晚时间时，将其提高到所选产品行数，例如仅分析 30m 产品时设为 9000。不在此处重新聚合 K 线，也不补充缺失价格。

## 配置与模块

`reversal_log` 是对数收盘价反转门槛，`.01` 是一项固定研究假设，另两值用于尺度敏感性描述。K 线产品与波浪尺度分别记录。其余默认参数及分类公式见已预先提交的 [识别规范](two_wave_recognition_spec_v0_1.md)，不得依据本次结果悄悄重写。

| 文件 | 职责 |
|---|---|
| `models.py` | 冻结配置、尺度 ID、版本 |
| `data.py` | 供应商视图与哈希核验、双时间口径 |
| `engine.py` | 流式拐点、完整周期、两浪配对、年龄与追加事件 |
| `geometry.py` | 五点漂移拟合、全部相关 close 包络覆盖、形态属性 |
| `replay.py` | 自包含回放、盲标、标注下载 |
| `annotations.py` | 独立标签校验、匹配、混淆矩阵、未验收状态 |

以上模块在 `src/factor_lab/visual_structure/two_wave/`。公开接口示例：

```python
from factor_lab.visual_structure.two_wave import Config, Engine, run_bars

engine = Engine(Config(timeframe="30m_offset_15", reversal_log=.01))
for bar in bars:
    new_events = engine.update(bar)
result = engine.export()
assert result == run_bars(bars, engine.config).export()
```

每条输入至少提供有时区的 timestamp/open/high/low/close，available_at 可选。引擎支持其他品种；仓库研究工作流限于已声明的中证1000开发数据。

## 输出与回放

每个产品/尺度目录包含 `pivots.jsonl`、`cycles.jsonl`、`structures.jsonl`、`events.jsonl`、配置、最终状态与摘要。记录以 ID 相联；全部源行情引用不可变数据路径及哈希，避免反复拷贝原始数据。总目录的 `run_manifest.json` 记录环境、源码和定义哈希，`summary.json` 记录每组计数、拒判、确认延迟和前缀检查。

打开 `cloud_results/two_wave_h0/replay.html`，选择产品/尺度和可见区间，使用截止序号、上一根、下一根、播放。文件内嵌 gzip 数据，不访问 CDN，需支持原生 `DecompressionStream` 的现代浏览器。内含完整打包数据，不能防止审查者主动阅读 HTML 源码；独立性仍依赖真实标注流程。

默认隐藏算法；显示算法后，会话后续标注被标记为非独立。看过后面的行情再回退，或跨尺度看到同一品种更晚行情，再在较早时点标注，后续参考降为 offline。刷新文件无法代替独立审查者清除其已获知识。需要严格 online 标注时，应从尚未见过的时间前缀单向推进，并保持独立的标注会话记录。

图中极值点可以画在发生位置，但其确认须等待之后的反转。bar-end 与 `information_available_time` 分列；源数据的 `available_at` 不证明早盘已实时可得。这里的 online 仅为按 K 线前缀的理想信息实验。

## 标注与验收

按 [预先冻结的评价协议](two_wave_evaluation_protocol_v0_1.md) 取样；初始模板无算法生成的真值。人工选择 3 点完整周期或 5 点连续两浪、相位、类别并导出 JSON。完整审查窗口与零散案例分开：只有完整审查窗口才能计算误检分母；offline/online 和不同 online 截止时刻分别评估。

评价接口为 `evaluate_annotations(export, document)`；`annotation_template(export)` 生成空模板。结构按相位、尺度、产品和五个极值各 ±2 根匹配，一对一最大匹配后二级最小总距离；混淆矩阵含未检出，端到端 F1 纳入漏检和误检。

无独立标签时 accuracy/precision/recall 保持空，状态为 `morphology_replication_not_yet_accepted`。当前仅实现点估计与初步门槛检查，相关样本的分块置信区间及双人仲裁工具尚未实现，评价函数不会自行授予形态验收、第三浪或交易权限。

## 结果理解

合成样例只检查实现性质。真实开发数据上的拒判率、边界事件、微扰稳定性是描述性结果，不是预测准确率、市场规律或可成交收益。多相位、多尺度及多视图高度重叠，不得把其计数当作独立样本量。

第一阶段尚未通过时保留现有 15 工具注册表，不发布第16工具的可用注册，不进入后续研究阶段。
