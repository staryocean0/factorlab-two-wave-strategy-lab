# Repository consistency maintenance — 2026-09-12

## Baseline and findings

The connector read found canonical `main` at
`ef29291535bc0fc239269ee9cb7c8e5a8512418c` (v0.7.6), while the v0.7.8 branch was
`ec0d49f1cec7d6c34d13af0fcfdb824687d57392`. This maintenance descends from the latter
so it contains the already completed v0.7.7 and v0.7.8 work; it does not restart them.

The previous README still called exact-ridge identity a current best component while
its later paragraphs demoted it. INDEX still said v0.6.48 awaited annotations before
appending its completed verdict. Human M0 opened with an older global status; machine
M0 was at v0.7.7 and retained an obsolete direction-transplant-next field. The ledger
mixed the 1,462-pair historical universe with later lifecycle-publication evidence.
The original AGENTS blanket external-data/resampling prohibition did not explain the
subsequently frozen v0.6.47 exception. The old governance writer could overwrite a
later control plane with v0.7.7 status. The only remaining workflow was CI; no residual
scientific one-shot workflow was present in the audited head.

## Applied cleanup

| Surface | Treatment |
| --- | --- |
| Machine M0 | Migrate current schema to 2.0; retain v1.32 detailed history as an exact archived blob; bind 43 current values/conditions to preserved evidence. |
| README / INDEX / human M0 / direction ledger | Archive original bodies and replace conflicting current sections with generated current views. |
| Current whitepaper / handoff | Add a current scientific whitepaper and root `CONTINUE_HERE.md`; distinguish code readiness, Development evidence and acceptance. |
| AGENTS | Replace old startup order and unscoped prohibitions with explicit current authority, historical exception and cloud/local execution policy. |
| Legacy scientific modules / tests / runner adapters | Retain unchanged for dependencies and historical regression; do not delete an adapter's base implementation. |
| v0.7.7 governance writer | Archive exact original; keep an import-only compatibility shim, with CLI exit 2 before any writes. Historical tests consume archived authority, not current M0. |
| CI | Archive exact seed recipe; replace automatic push/PR execution with a manual, double-opt-in verification recipe calling the same local runner. |
| Source/data closure | Keep original 473-entry manifest unchanged; only the old CI recipe relocates, and its original hash is still checked. Keep src/shared/data trees unchanged from the baseline. |
| Frozen whitepapers / user specs / versioned protocols / negative results | Retire obsolete execution authority but preserve original files in place, avoiding broken imports, rewritten evidence or destroyed provenance. |

The schema-2.0 current authority supersedes schema 1.32 as current control-plane
configuration. Historical numeric details and forbidden-shortcut lineage remain in
the pinned archive; compacting the current view is not deletion of scientific evidence.
A maintenance revision is not scientific v0.7.9 and grants no new research/runtime authority.

## Automatic consistency guards

`scripts/check_repository_consistency.py` checks explicit false/null authority,
case/publication denominator consistency, evidence bindings and archived hashes,
full generated-document equality, current link existence, workflow gating, the
source-manifest pin, tracked-file lifecycle coverage, protected code/data tree hashes,
and Python/shell syntax. It emits a per-file role inventory on a complete checkout.
It does not claim full regression or rerun scientific outcome scripts.

`scripts/verify_repository.py` is the shared local/manual-CI entrypoint. A full pass
requires Python 3.11, the consistency scan, original source/data validation, and full
pytest. Wrong interpreters, missing files and failed steps remain explicit failures.

## What actually ran in this session

Current-session environment: Python 3.13.5 / pytest 9.0.2. The **89 maintenance
regressions passed**, including synthetic fail-closed fixtures and actual generated
document equality. The five authored/modified Python files parsed successfully.
The full verification environment guard was exercised and correctly returned exit 2
(`blocked_environment`) on Python 3.13; this is **not a full pass**.

The terminal could not resolve GitHub for a complete clone; connector reads/writes
remained available. A complete supported checkout, Development parquet access and
pyarrow were not available in the current container. Therefore the complete tracked
inventory scan, full source/data validation and original full pytest suite were **not
executed here**. No Actions job was dispatched or rerun. Historical green CI does not
certify the changed maintenance code.

Machine-readable receipt: [current-session verification](CURRENT_SESSION_VERIFICATION_20260912.json).
Full-environment task: [TW-CONSISTENCY-20260912-01](cloud_local_communication.md).
The maintenance branch must remain a draft integration candidate until the full local
receipt is returned and reviewed; do not claim that main or every component is already
fully verified. Final changed-file and preserved-tree metadata can be independently
checked against the PR and the lifecycle manifest.

## Same-day maintenance integration

A final pre-publication branch check also found the earlier eight-commit cleanup at
`49bae1a2d1cfb6ffc2fc4e520f6ff5553506bc9c`. The integration preserves that history and
explicitly resolves overlapping changes rather than overwriting the branch or leaving
two competing current authorities. Its valid public-visibility and consumed-external-
validation corrections are adopted under `docs/governance/current/`. The original
seed declarations remain hash-preserved and explicitly historical; the active package
validator consumes and checks the current declarations against M0.

Ten additional declaration consistency/failure-injection tests passed, bringing the
maintenance total from 79 to 89. No original scientific regression was removed from
the common scientific baseline. Full Python 3.11/source/data verification remains
pending. See [explicit reconciliation](../governance/MAINTENANCE_RECONCILIATION_20260912.md)
and [current declarations](../governance/current/README.md).
