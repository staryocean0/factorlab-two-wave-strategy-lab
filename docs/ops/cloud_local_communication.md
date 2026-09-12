# 云端—本地沟通记录

## TW-CONSISTENCY-20260912-01：仓库整理后的完整环境验收

状态：`awaiting_local_full_checkout_verification`。本记录不是已自动派发的任务。

目标：对本次维护分支的精确提交完成源文件/数据完整性检查及完整 pytest；不重跑科研实验。
维护分支：`maintenance/repository-consistency-v0708-20260912`。
基线：`ec0d49f1cec7d6c34d13af0fcfdb824687d57392`（包含 v0.7.8 裁决）。
执行前记录 `git rev-parse HEAD`；反馈必须绑定实际检验提交，不能只写分支名。

### 云端已完成与缺口

通过 GitHub connector 读取主线、最新裁决、原始封存清单、工作流和关键入口；进行文档、
治理脚本、测试及工作流整理。当前会话仅有 Python 3.13 / pytest 9，未取得完整 Git checkout
与数据，且无 pyarrow；直接 clone 因当前终端无法解析 GitHub 域名失败。
新增维护代码的可执行单元/语法检查与源码树哈希复核应见同目录审计记录；它们不是完整验收。
Actions 配额不可用，未主动派发或重跑；不要用 Actions 绕过本地验收。

### 本地需要的最小环境与命令

需要本仓完整 checkout（包括已有 Development parquet、原始依赖和本次归档文件）以及
Python 3.11；不需要新增市场数据、不需要新标签、不需要搬运其他项目全部数据。
切换到上面的维护分支，确认无本地科研代码或数据改动，然后从仓库根目录执行：

```bash
git rev-parse HEAD
git status --short
python3.11 -m venv /tmp/two-wave-verify-venv
/tmp/two-wave-verify-venv/bin/python -m pip install -e .
/tmp/two-wave-verify-venv/bin/python scripts/verify_repository.py \
  --report /tmp/two-wave-verification.json
```

验收要求：共享入口返回 0；报告状态 `passed_full`，三个步骤返回码均为 0；完整 pytest
实际执行。保留源清单原有哈希、全部历史正式裁决和科研源码/数据；不调参数、不授予形态/
交易/生产权限。失败项原样报告，不得通过删测试、改科学门槛或弱化封存检查变绿。

### 反馈模板（由实际执行方填写）

- 实际提交、Python/依赖环境、执行位置：待填。
- 命令/退出码/完整测试通过和失败数量：待填。
- `/tmp/two-wave-verification.json` 的小报告回传位置：待填。
- 失败、未执行与未验证项目：待填。
- 本地已反馈：否。云端已复核：否。

大数据留在本地，只回传小报告。云端收到后核对提交、输出和差异，再决定是否合并；不得把
本地反馈改称云端独立完整复验。新证据可用性仍按 v0.7.8 另行处理，本验收不开放 v0.7.9。
