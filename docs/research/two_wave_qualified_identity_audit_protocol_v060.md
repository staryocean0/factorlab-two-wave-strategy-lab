# v0.6.0 Frozen protocol — qualified financial identity vs exclusive packing

## Purpose

Determine whether the observed native-5m cross-slicer identity instability is primarily introduced by the exclusive selected-event packing layer, or already exists in the frozen qualified morphology candidate pool.

This is an **identity-layer audit**, not a direction-model POC.

## Frozen upstream

- v0.5.2 exact-ridge parent identity;
- v0.5.4 full-cycle qualification;
- all v0.4.3 hard qualification thresholds except the already-frozen v0.5.4 leg-duration demotion;
- supplied `5m_offset_0..4` only;
- development period through 2020-12-31 only;
- no local price resampling.

No recognizer, qualification or direction formula may change in this experiment.

## New component only

`morphology_identity_v060.py`:

1. canonicalize qualified records by `(phase, five_occurrence_bars)` inside each view;
2. publish the identity once at the first confirmed qualified member; later same-anchor scale births append evidence and never rewrite the identity event;
3. retain birth-scale member IDs/levels in the audit evidence stream;
4. do not suppress rolling/overlapping two-wave identities;
5. export legacy `selected_any` only as a packing diagnostic;
6. for cross-view audit only, attach five occurrence timestamps from the supplied view bars.

## Required single-view assertions

For every view:

1. every canonical member was already `scale_qualified=true`;
2. no rejected record is rescued;
3. canonicalization changes no member geometry or D1 label;
4. exact same-anchor members may merge only if phase and direction geometry are identical;
5. rolling overlapping identities remain distinct;
6. no future outcome/trading field can influence identity;
7. prefix invariance is exact at the immutable identity-event layer: a later same-anchor scale member may append evidence but may not mutate an already-published identity; this must be tested explicitly on frozen prefixes when raw data is available.

## Cross-view audit relation

For `5m_offset_0` versus each of `offset_1..4`:

A strict identity edge exists iff:

- start phase is identical;
- the ordered five occurrence timestamps are compared position-wise;
- all five absolute timestamp differences are `<= 5 minutes` (one nominal bar width).

No interval IoU, D1/D2/PAWCT label, amplitude, return or outcome participates in the edge.

Only **mutual-unique** strict edges are counted as same financial-event matches. Ambiguities are reported and never resolved by a post-hoc tie-break.

## Required outputs

Per view:

- qualified record count;
- canonical qualified identity count;
- exact-anchor duplicate scale-evidence groups;
- canonical identities with/without a legacy selected member;
- overlap-component diagnostics for the qualified pool.

Per offset pair:

- mutual-unique strict matches among canonical qualified identities;
- ambiguity counts/rates;
- unmatched counts in each direction;
- same metrics after restricting to legacy selected identities;
- number/fraction of strict qualified cross-view matches hidden because one or both sides were overlap-suppressed by the legacy ledger;
- D1/D2/PAWCT agreement may be reported **only after** strict identity matching and is diagnostic, never used to select matches.

## Route decision

The architecture decision is semantic and does not depend on performance: exclusive packing no longer has authority to define morphology identity.

The empirical route decision is:

- **Route Q (qualified identity adequate):** canonical qualified identities show a clear, low-ambiguity mutual-unique local-match structure across all four offsets, materially stronger than the legacy selected-only match structure. Then return to direction adjudication on strict same-event pairs, with PAWCT still unpromoted.
- **Route U (upstream identity still unstable):** qualified canonical identities themselves remain mostly absent/ambiguous across harmless offset changes. Then do not touch direction; return to ridge/qualification identity research.
- **Route M (mixed):** packing hides substantial stable identities but qualified identity is still materially unstable. Keep packing downstream and continue upstream identity research.

No post-hoc numeric cutoff may be invented after seeing the five-view replay. Report the full per-view decomposition and make any later numeric acceptance gate a separately frozen experiment.

## Current execution constraint

GitHub Actions quota is exhausted. This protocol must be executed locally against the frozen repo data when those parquet files are available in the active runtime. Existing historical Actions artifacts may be read, but no new workflow run or rerun is permitted.

## Status until replay

`morphology_identity_layer_decoupled_in_preanalysis_pending_local_five_view_replay`

Operational baseline remains v0.4.3. Global status remains `morphology_replication_not_yet_accepted`.
