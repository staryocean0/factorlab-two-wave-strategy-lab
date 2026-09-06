# 云端—本地沟通记录

> 本文按仓库 `AGENTS.md` 的“云端—本地交接协议”维护。当前协作协议已由用户明确启用。

## CL-20260906-001 — v0.5.2 extremum-ridge 正式六视图本地补执行

### 状态

- 云端已诊断：`handoff_required`
- 本地执行：`pending`
- 云端复核：`pending`
- 研究权限状态：仍为 `morphology_replication_not_yet_accepted`
- 当前 operational baseline：仍为 `v0.4.3`

### 任务目标与所需结论

在**不修改冻结数学定义、资格规则、D1、数据口径和案例门槛**的前提下，对 v0.5.2 exact extremum-ridge recognizer 完成正式六视图计算并产出可复核结果，以便云端继续按 `docs/research/two_wave_extremum_ridge_protocol_v052.md` 判定：

1. 六个视图是否完成全量运行；
2. 18 个 prefix replay（每视图 25% / 50% / 75%）是否全部固定前缀不改写；
3. lineage anomaly 是否保持为非正常大尺度现象；
4. v0.5.2 相对 v0.5.1 是否真正改善 parent identity / micro-pivot absorption；
5. 5m offset IoU 是否不再系统性劣于 v0.4.3；
6. case00、case02、case10、case11、case14 与固定 2018/2019/2020 审计是否满足冻结协议；
7. 最终应进入 `parent_identity_pass_qualification_pending`，还是判定 TCSS hierarchy route failed 并转向 trailing SSA / causal wavelet-filter-bank POC。

本任务**只做 morphology / causality adjudication**。禁止开启 H1/H2、第三浪、收益率、交易、OOS、paper trading 或 production。

### 冻结代码身份

- Repository: `staryocean0/factorlab-two-wave-strategy-lab`
- Branch: `codex/two-wave-phase1-20260905`
- Formal six-view frozen commit: `b8ab88b470dc9c73103a3957be00f79d339440bd`
- Parent causal-fix commit: `63cf53da5137f12a54df12e346d8669e95ba6b5e`
- Core implementation: `src/factor_lab/visual_structure/two_wave/extremum_ridge_v052.py`
- Runner: `scripts/run_two_wave_extremum_ridge_v052.py`
- Frozen protocol: `docs/research/two_wave_extremum_ridge_protocol_v052.md`

若本地工作区已有其他改动，不要覆盖或混入本任务。优先在 detached worktree / 干净 worktree 中对上述 commit 执行。不得因结果不理想改参数、改 case、改 matching gate、改资格阈值或改 scale 定义。

### 云端已完成的步骤与证据

1. v0.5.2 synthetic：已通过，387 tests。
2. corrected main-5m causal smoke：已通过。
   - Actions run: `33972409920`
   - main `5m_offset_0`: births 38636 / anomalies 0 / eval 38049 / qualified 425 / selected 256
   - 3 个 main-prefix smoke checks 全通过。
3. 正式六视图 Actions run 已发起但未完成：
   - run: `33973525292`
   - job: `101326120069`
   - commit: `b8ab88b470dc9c73103a3957be00f79d339440bd`
   - package validation：success
   - full pytest regression：success
   - formal calculation：runner 在 1m 阶段收到 shutdown signal，exit code 143；**不是算法断言失败**。
4. 在 shutdown 前，五个 5m full-view 已打印完成：
   - `5m_offset_0`: births 38636 / anomalies 0 / eval 38049 / qual 425 / selected 256
   - `5m_offset_1`: births 37176 / anomalies 0 / eval 36624 / qual 376 / selected 225
   - `5m_offset_2`: births 37062 / anomalies 0 / eval 36499 / qual 391 / selected 240
   - `5m_offset_3`: births 36937 / anomalies 0 / eval 36378 / qual 406 / selected 242
   - `5m_offset_4`: births 36689 / anomalies 0 / eval 36164 / qual 418 / selected 253
5. 该失败 run 没有上传 artifact，因此不能仅凭云端日志完成正式 adjudication。

### 阻断原因

云端当前没有可直接持续运行该仓库全量计算的本地执行环境；GitHub Actions 又在正式六视图运行中被 runner 外部 shutdown。根据 `AGENTS.md` Protocol 2，此时不应继续用 Actions 反复重跑，而应转交拥有本地数据/算力环境的本地大模型执行。

### 所需最小数据与口径

只使用仓库已供应的 development material：

- 标的：`000852.SH` CSI1000 index signal data
- 日期：2015-01-05 至 2020-12-31
- 视图：runner 自带的 `5m_offset_0..4` + `1m_official`
- 使用供应的 DataHub-built bar views；**不得本地重新 resample wall-clock frequency**
- 禁止下载、推断、补造 2021+ 数据
- 禁止引入独立于冻结 runner 的额外市场数据

如果本地仓库缺上述已供应数据，只报告缺失的具体文件/视图；不要联网补数据。

### 本地实施步骤

以下命令对应冻结 runner，当前仓库已有可执行器。可根据本地 Python 环境调整虚拟环境激活方式，但不要改变研究脚本逻辑。

```bash
# 1) 在干净工作区确认代码身份
git rev-parse HEAD
git status --short

# 若当前 HEAD 不是冻结 commit，建议使用独立 worktree，避免覆盖现有工作：
# git worktree add ../two-wave-v052-local b8ab88b470dc9c73103a3957be00f79d339440bd
# cd ../two-wave-v052-local

# 2) 安装冻结项目依赖
python -m pip install -e . editables==0.6

# 3) 包与数据边界校验
mkdir -p local_results/v052_six_view_proof/source
python scripts/validate_theme_package.py \
  | tee local_results/v052_six_view_proof/package_validation.json

git rev-parse HEAD > local_results/v052_six_view_proof/commit.txt

# 4) 全回归
python -m pytest -q --junitxml=local_results/v052_six_view_proof/tests.xml \
  | tee local_results/v052_six_view_proof/tests.log

# 5) 正式六视图 + 18 prefix replay + offset stability
python scripts/run_two_wave_extremum_ridge_v052.py \
  --output local_results/two_wave_extremum_ridge_v052_six_view \
  | tee local_results/v052_six_view_proof/research.log

# 6) 确认执行未偷偷修改冻结研究文件
git diff --exit-code -- data src tests scripts docs/research pyproject.toml

# 7) 保存环境与冻结源码身份
python -m pip freeze > local_results/v052_six_view_proof/environment.txt
cp src/factor_lab/visual_structure/two_wave/extremum_ridge_v052.py \
  local_results/v052_six_view_proof/source/
cp tests/unit/test_two_wave_extremum_ridge_v052.py \
  scripts/run_two_wave_extremum_ridge_v052.py \
  docs/research/two_wave_extremum_ridge_protocol_v052.md \
  local_results/v052_six_view_proof/source/
```

如果一次完整 runner 在本地也因资源原因中断：

- 不修改数学规则来“让它跑完”；
- 记录中断视图、退出码、峰值内存/资源错误；
- 可以实现**仅执行层面的 resume / view selection**，但必须证明它只改变调度、不改变算法输出，并把该调度补丁单独提交/记录；
- 在云端复核该调度补丁前，不把分段结果称为正式 protocol pass。

### 预期输出

至少保留：

- `local_results/two_wave_extremum_ridge_v052_six_view/summary.json`（若 runner 使用其他实际名称，以实际生成结果为准）
- runner 生成的六视图结果、prefix checks、offset stability、fixed-day audits、legacy case audits
- `local_results/v052_six_view_proof/package_validation.json`
- `local_results/v052_six_view_proof/tests.log`
- `local_results/v052_six_view_proof/tests.xml`
- `local_results/v052_six_view_proof/research.log`
- `local_results/v052_six_view_proof/commit.txt`
- `local_results/v052_six_view_proof/environment.txt`
- `git diff --exit-code` 的退出状态

大文件留在本地，不要求上传原始市场数据。回传云端只需要小型 JSON / Markdown 摘要以及必要结果文件，或把本节下方“本地反馈”填写后提交到同一文档。

### 冻结验收条件

本地模型**只报告事实，不自行宣布 promotion**。云端后续按冻结 protocol 复核，重点包括：

1. 六个视图全量完成；
2. prefix checks = 18 且全部 `all_passed` / rewrite count 0；
3. lineage anomaly 不成为正常大尺度现象；
4. selected / qualified micro-pivot absorption 相对 v0.5.1 有实质改善，不能只看 coverage 增大；
5. 5m offset IoUs 不得像 v0.5.1 那样对 v0.4.3 全面系统性恶化；
6. case00 必须能审计到与 v0.5.0 middle-scale parent structure 对应的 ridge identity；资格层可另行拒绝；
7. 2018/2019 identity 不应跳到无关 coarse family；
8. case02 的 90/3 假第二浪不得复活；
9. case11/14 不得发布 multi-week giant tuples；
10. 不以 publication count、coverage、range 数量或 P&L 作为 promotion 理由。

### 本地反馈模板

本地模型完成后，请直接在本任务下补充以下内容；不要删改上面的云端记录。

```markdown
#### 本地反馈 — CL-20260906-001

- 实际执行代码 commit：
- 工作区是否干净：
- Python / OS：
- 数据范围：
- 数据身份/摘要（只需必要摘要，不上传大数据）：
- package validation 命令与 exit code：
- pytest 命令、测试数量与 exit code：
- formal runner 命令与 exit code：
- 六视图是否全完成：
- prefix checks：通过数 / 总数；rewrite count：
- lineage anomalies（逐视图）：
- 每视图 births / eval / qualified / selected：
- selected/qualified absorption median、p90、with_absorbed：
- v0.5.2 5m offset IoUs：
- v0.4.3 对照 IoUs（如 summary 内提供）：
- case00：
- case02：
- case10：
- case11：
- case14：
- 2018/2019/2020 fixed-day audit：
- 结果目录：
- 小型 summary / report 路径：
- 失败或未验证事项：
- 是否对 runner 做过仅执行层补丁：若是，附 commit/diff 与理由
```

### 云端后续动作

收到本地反馈后，云端将：

1. 先区分“本地已反馈”与“云端已复核”；
2. 复核代码身份、数据边界、退出码、18 prefix、offset stability 与案例审计；
3. 写 `docs/research/two_wave_extremum_ridge_results_v052.md`；
4. 决定：
   - `parent_identity_pass_qualification_pending` → 才激活单组件 qualification 实验；或
   - TCSS exact-ridge identity 仍失败 → 停止继续深挖 TCSS，转 trailing SSA / causal wavelet-filter-bank POC；
5. 保持 PR Draft，不 merge main；
6. 在 morphology acceptance 前不进入 H1/H2、third-wave、returns 或 trading。
