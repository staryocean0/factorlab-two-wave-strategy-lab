# Same-day maintenance reconciliation

## Inputs and history

Common scientific baseline: `ec0d49f1cec7d6c34d13af0fcfdb824687d57392`.
Earlier maintenance branch: `maintenance/repository-consistency-refresh-20260912`,
observed at `49bae1a2d1cfb6ffc2fc4e520f6ff5553506bc9c` (eight commits ahead of the baseline).
Current-session first maintenance candidate: `e557df51f1420b0b7f82abe3d91da03109fad84b`.
The final integration records both maintenance histories as parents and uses the
explicit resolved surface described below. Neither source branch is force-updated
or deleted. This is not a claim that both competing configurations are active.

## Explicit resolutions

| Earlier maintenance surface | Resolved treatment |
| --- | --- |
| README, INDEX, AGENTS, human M0, M0 schema 1.33 and component-status file | One current M0 schema 2.0, six generated current documents and one lifecycle manifest replace competing current-state declarations. The complete earlier implementation remains in its parent commit. |
| Rewritten broad imported ai-readme, 00-index, ops/user indexes | Original seed bytes remain frozen in place and are classified as historical/imported references. Current startup uses AGENTS, CONTINUE_HERE and docs/INDEX. Historical instructions do not authorize execution. |
| Public repository visibility correction | Adopted in `current/package_scope.json`: public, no private-repository requirement, no authority escalation. |
| Already-consumed external validation correction | Adopted in `current/data_usage_declaration.json`: distinguish shipped 2015-2020 Development rows from the separately frozen, already-consumed 2024/2025/2026 temporal material. No fresh-evidence or new-execution grant. |
| Original seed package/data declarations | Preserved at their original paths/hashes for source closure, explicitly superseded as current declarations by the `current/` versions. The validator reads the current declaration for authority checks. |
| Alternative repository-consistency code inside scientific src and its tests | Not installed as a second schema-specific control plane. The stdlib maintenance checker, shared verifier and 89 maintenance regressions cover the selected current design, including new declaration consistency checks. Scientific src/shared/data trees remain identical to the common baseline. Earlier tests and helper source remain recoverable in the recorded parent. |
| Mutating apply-refresh script | Retained in earlier history, not installed as an active writer. Current documents use a fixed six-file generator; the old v0.7.7 governance CLI fails closed. |
| Added runner/test/source navigation and v0.7.8 result card | Preserved in earlier commit history; the current index, whitepaper, lifecycle manifest and audit provide the resolved navigation without treating historical guidance as current authority. Existing baseline experiment evidence is untouched. |
| Automatic CI and future one-shot assumptions | Not adopted. The selected workflow is manual, double-opt-in, read-only, and uses the same verification entrypoint as local execution. No Actions dispatch or rerun was performed. |

Current declarations identify the source maintenance commit. Both maintenance attempts
found the same stale-current-status problem; adopting their factual corrections does
not justify copying mutually incompatible authority schemas, validator exceptions or
execution assumptions together.

## Verification and merge boundary

The reconciled current-session maintenance suite passed 89 tests. Those tests include
actual generated-document equality and declaration/M0 comparisons plus synthetic
failure-injection fixtures; they are not a full market-data or scientific regression.
A full Python 3.11 checkout must still complete `scripts/verify_repository.py` and
return a receipt tied to the exact final integration commit. Task:
`TW-CONSISTENCY-20260912-01`, recorded in `../ops/cloud_local_communication.md`.

Keep the integration as a draft PR until that receipt is reviewed. Do not represent
the prior branch's existence, historical green runs, or the new maintenance tests as
main acceptance. The scientific checkpoint remains blocked v0.7.8, with no new
candidate, direction scoring, reference labels or runtime authority.
