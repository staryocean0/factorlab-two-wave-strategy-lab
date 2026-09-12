# 策略渐进开发与训练后账户审计工作流

## 何时使用

每次创建、调整、组合或重训策略/多因子模型时，先按 `$strategy-slice-rebuild` 完成数据边界、年度材料和整案重建，然后使用本工作流分层记录进步并执行训练后账户审计。

## 决策顺序

1. 先评估硬原理：金融、数学、时序、完整账户、确定性、source closure、多重尝试和权限。失败即停止经济解释。
2. 在结果前声明主目标、比较器、账户/成本口径和数值重放容差。
3. 硬门全过后，主目标改善只要超过数值容差，就写入 `progression_ledger`；不设最低收益或效果强度门。
4. 分布、回撤、成本、时钟和集中度可以决定是否晋升当前研究快照，但不能删除已保留的进步。
5. 收益/回撤、双时钟或其他金融效用冲突若未在结果前冻结权重，标记 `progress_tradeoff_waiting_financial_owner`；禁止 AI 事后自定偏好。
6. 任何回溯晋升仍是 `fresh_oos=false`；生产权另行审计。

## 训练后 A0—A7

1. **A0**：冻结 model/checkpoint/score identity，禁止账户结果回流续训。
2. **A1**：结果前冻结 TopN、权重、买不到处理、集中度、成本压力、时钟/variant 和尝试分母。
3. **A2**：由策略适配器产生带 `available_at` 的 score、raw/PIT market 和 group exposure 树。
4. **A3**：验证 formal/isolated、会计恒等式、source closure 和精确 workload 性能。
5. **A4**：单独命令只盲测上年冻结账户政策。
6. **A5**：主控审阅 blind evidence 后，另一命令重价完整家族，分别产生 progression 与 promotion ledger。
7. **A6**：封存 blind、analysis、family 和 session receipts，下年同时绑定 prior receipt/policy digest。
8. **A7**：结果中性审计所有合法终态，不得写死“必须无胜者”。

## 迁移现有 REAKA P7

不重跑、不改写 P7 历史结论。用 successor migration ledger 索引以下材料：2014 Top50 临时晋升；2015 收益/回撤冲突；2016—2019 仅 14:30 的改善；2020 Top50 在 14:30 的正增量与 14:45 的负增量；14:45 时钟 7/10 正年但季度分布不足。

这些只是下一轮新预登记的材料，不是已晋升策略或新鲜证据。

## 基础设施验证命令

```bash
.venv/bin/python scripts/build_strategy_progressive_development_workflow.py --overwrite
.venv/bin/python scripts/validate_strategy_progressive_development_workflow.py
.venv/bin/pytest -q tests/unit/test_strategy_progressive_development.py
.venv/bin/python /home/starryocean/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/strategy-slice-rebuild
```

每个具体策略在 A1 与 A7 使用：

```bash
.venv/bin/python scripts/freeze_post_training_account_audit_plan.py \
  --input <result-free-plan-input.json> --output <frozen-plan.json>
.venv/bin/python scripts/validate_post_training_account_audit.py \
  --plan <frozen-plan.json> --receipt <completed-audit-receipt.json>
```

策略适配器负责生成输入和执行账户；上述通用命令只冻结身份、验证阶段分离、尝试分母、双树一致和权限。
