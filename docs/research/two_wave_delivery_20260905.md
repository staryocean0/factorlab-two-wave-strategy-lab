# 第一阶段研究交付说明（2026-09-05）

用户在获知本地完整审查包上传曾被自动审批拒绝后，已明确同意将审查包和回放写回同一私有仓库 `staryocean0/factorlab-two-wave-strategy-lab` 的研究分支 `codex/two-wave-phase1-20260905`。本次交付包含下列三个未经改写的文件；附上本说明，以保留原报告和审查包的字节一致性。

原报告中的“待用户确认上传”描述的是此前状态，本说明更新该交付状态。上传获得许可不等于形态验收、第三浪研究或交易授权。当前研究状态仍为 `morphology_replication_not_yet_accepted`。

## 审阅入口

- [研究报告](two_wave_phase1_report_20260905.md)：六个本地视图的详细分析，以及 GitHub 全量运行的日志证据。
- [完整本地审查包](../../cloud_results/two_wave_local_records.zip)：189 个文件，包含报告、详细记录、空标注模板、回放、敏感性结果、合成样例和远端日志摘要。
- [独立逐根回放](../../cloud_results/two_wave_h0/replay.html)：下载后在支持 `DecompressionStream` 的现代浏览器中打开。HTML 自包含，无外部脚本或样式依赖。此次交付没有完成浏览器交互验收。
- [实现和使用说明](two_wave_runbook.md)。

报告中的 `summary.json`、`run_manifest.json`、敏感性及合成图等相对链接指向审查包展开后的目录。请下载 ZIP，保留目录结构解压后查看这些链接；这些详细记录没有作为单独文件全部写入 GitHub。ZIP 自身下载链接无需在 ZIP 内自包含。

## 结果范围与溯源

本地审查包来自 6 个供应商视图 × 3 个固定尺度，18,992 源文件行（视图重叠），8,208 个结构。它不是 GitHub 全量 14 个视图的结果包。回放每个运行包含前 1,200 根 K 线，完整统计不受该展示上限影响。

代码与冻结规范的来源提交为 `f0ae399e76e962c6dcc29a5c5e0611430dcd88c8`。本次仅补充交付文件，不修改识别代码、规范、数据或十五工具注册表。

[GitHub 已完成的全量研究运行](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/actions/runs/33944192487)覆盖 14 个视图 × 3 个尺度，42/42 前缀检查、125 项测试通过。全量原生产物 ID 为 `9962860884`，按原工作流保留 30 天；其下载在本工作区此前返回 HTTP 403，尚未读取全量产物内部详细结果，不将本地六视图拒判率外推到十四视图。

当前已分析的本地运行明确分类覆盖仅 2.73%–6.27%，缺少独立人工标签，形态尚未验收。本次上传不改变该结论。

## 文件校验

ZIP 的 189 项均通过 CRC 校验；包内报告和回放与独立文件逐字节一致。ZIP 不含原始 Parquet；回放和结果仍包含私有开发行情的衍生内容。

| 文件 | 字节数 | Git blob SHA-1 |
|---|---:|---|
| `cloud_results/two_wave_local_records.zip` | 11,656,149 | `1599acc79b9c9a4103e4e36995d3165e0a45acf6` |
| `cloud_results/two_wave_h0/replay.html` | 6,200,981 | `741d8f3d657aeed411ff7527ad9828040a2a8fcb` |
| `docs/research/two_wave_phase1_report_20260905.md` | 21,758 | `b313198526b71d6f9b3c95d68af3514e044a4c7f` |

SHA-256：

```text
5137fc3c9bfd2a1905b33750d607144b513010e0707ebb909ca456726eb21bb6  cloud_results/two_wave_local_records.zip
7aba33666c8e657695119a1975f24275ae50a69639976f4993e5f7cbbe29b9c5  cloud_results/two_wave_h0/replay.html
ef12bff436fe4c0b082b7a76c00e51084627309673b54261669a27ec49c9350b  docs/research/two_wave_phase1_report_20260905.md
```
