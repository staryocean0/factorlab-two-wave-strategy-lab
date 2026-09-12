# Two-Wave research control plane — current entry

Read `CONTINUE_HERE.md`, `experiments/two_wave_m0_authority.json`,
`docs/governance/REPOSITORY_LIFECYCLE.json`, `docs/INDEX.md`, then the
specific frozen protocol/evidence required by the task.

## Scope and authority

This is the bounded research repository for `two_wave_parent_structure_recognizer`:
two complete same-scale waves and parent Range / UpTrend / DownTrend / Uncertain.
It is not a tradable signal, an execution service, or permission to promote a strategy.
The latest scientific checkpoint is v0.7.8; use the machine authority for its exact
status and reopening conditions. Repository maintenance does not open v0.7.9.

M0 schema 2.0 is the sole current scientific control plane. Schema 1.32 and the
superseded current-document bodies are archived byte-for-byte. Historical next-step
sentences in archived or versioned documents are not current execution instructions.
`ai-readme.md`, `docs/00-index.md`, and the original `docs/user/` handoff prompts are
frozen imported references, not current startup instructions. Current whitepaper:
`docs/research/TWO_WAVE_CURRENT_WHITEPAPER.md`.

Keep morphology acceptance, trade/production/registered-use authority and fresh-OOS
claims false. Keep active semantic-parent authority and direction winner null.
Do not reopen in-sample rescue, retune qualification/direction thresholds, turn 19
publication rescues into a claim of semantic improvement, or discard v0.6.47/v0.6.48
negative evidence. Maintenance and external-evidence availability are separate tasks.

## Frozen infrastructure and data

The immutable `tool_registry_v1_5` prefix contains exactly 15 tools. The proposed
16th identity is a research-only candidate slot, never an installed tool.
Layer 3 architecture and strategy-identity registry remain at 2.2; imported Layer
1/2/3 contracts are dependencies, not additional active strategy mandates.

Shipped CSI1000 signal data remain 2015-01-05 through 2020-12-31 Development material.
Do not edit, interpolate, relabel or expand `data/development/`. Index prices are not
IM/ETF/options fill prices. Preserve UTC bar-end ordering and original source-clock
provenance. No PnL, future returns or future lifecycle states may define morphology.

The closed v0.6.47 protocol was an explicitly scoped exception: it used separately
frozen post-2020 temporal material and a five-offset constructor validated against
native bars. This is historical validation, not a standing download/resampling grant
and not globally fresh OOS. No new external scoring is currently open. New evidence
must meet both v0.7.8 prerequisites and a separately preregistered protocol.

Keep the source-closure manifest unchanged. Its original hashes remain binding;
the sole relocated frozen entry is the old CI recipe, whose exact archived bytes
are checked instead. Do not weaken scientific source/data checks to make cleanup pass.
Retain all scientific libraries and regression tests; old versions may still be
required by transplantation, adapters, imports, or evidence replay.

## Safe maintenance and verification

Generated current documents must be changed through the machine authority and
`scripts/check_repository_consistency.py --write-docs`, not by appending competing
current-status paragraphs. A new lifecycle role or archive requires a manifest entry.
Use `python scripts/verify_repository.py --report /tmp/two-wave-verification.json`
on a complete Python 3.11 checkout. Full verification includes consistency, source
and data validation, and the complete pytest suite. A static pass is not a full pass.
The v0.7.7 governance writer is retired; its import-only compatibility API reproduces
historical facts without granting permission to write current authority.

## 云端—本地协作与执行限制

本项目云端任务的执行顺序是：当前会话直接执行 → 本地大模型 → GitHub Actions 最后。
当前 Actions 额度不可用；不主动派发、重跑或用连续 push 试探额度。提交使用 `[skip ci]`。
保留的 CI 仅为手动、双重明确授权后可用的验证配方；不能把跳过或未运行写成通过。

当前会话能完成的读取、修改、静态验证和单元检查自行完成。不能完成的完整环境检查，
写入 `docs/ops/cloud_local_communication.md`：任务编号、代码版本、最小缺口、可执行命令、
预期产物、验收条件与实际已做范围。无本地执行通道时，不声称已自动派发。
本地反馈必须记录执行环境、提交、命令/退出码和未验证项；云端复核后再分别标记
“本地已反馈”和“云端已复核”。不要求默认搬运全部原始数据，不制造绿色 CI，
不删除合并保护。该协作协议不扩大研究、金融验收或生产权限。
