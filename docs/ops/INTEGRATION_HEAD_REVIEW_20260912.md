# Final integration-head review — 2026-09-12

The initial audit observed main at `ef29291535bc0fc239269ee9cb7c8e5a8512418c`.
Before draft-PR publication, a new connector read observed main at
`152ae1ef11a04bb3b434da25025794db7a706c81`, whose parent is the reconciled earlier
maintenance head `49bae1a2d1cfb6ffc2fc4e520f6ff5553506bc9c`.

This is an externally advanced main, not a main update performed by this maintenance
candidate. Main now has M0 schema 1.33 and the closed v0.7.8 evidence-gap status.
The candidate's schema 2.0 remains proposed until the draft is fully verified and
reviewed. Do not present the initial v0.7.6 observation as the current main state.

## Reviewed final main delta

The additional commit changes only compatibility navigation in README, ai-readme,
00-index and ops/user indexes. It keeps the four-layer timing inventory reachable
and distinguishes data clock, bar measurement, research/decision semantics, and
execution instrument routing. It changes neither the scientific verdict nor its
acceptance boundary.

The candidate already preserves the frozen four-layer inventory and whitepaper as
explicit links in the generated current `docs/INDEX.md`; AGENTS and the current
whitepaper distinguish those infrastructure dependencies from scientific/runtime
authority. The latest main commit is included as an integration parent. The selected
current views and the historical-role resolution documented in
`../governance/MAINTENANCE_RECONCILIATION_20260912.md` remain intentional; blindly
combining both index bodies would recreate competing current guidance.

## Publication and verification limits

Review branch: `maintenance/repository-consistency-v0708-20260912`.
The final draft incorporates both earlier maintenance histories and the observed
latest main ancestry. Neither main nor either original research/maintenance branch
is force-updated or deleted. Any later concurrent main commit requires a new review,
not a claim that this snapshot automatically covers it.

The same 89 maintenance regressions passed on the authored code; this last change is
an integration record, not a new scientific computation. Full supported Python 3.11
source/data/full-pytest verification remains outstanding under
`TW-CONSISTENCY-20260912-01`. No Actions job was dispatched or rerun.
