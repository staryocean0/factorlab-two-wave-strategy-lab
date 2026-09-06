# v0.6.2 Frozen protocol addendum — causal member representative

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.2 AUDIT OUTPUT IS READ**

This addendum only resolves one implementation ambiguity in `two_wave_raw_projection_identity_protocol_v062.md`. It does not change the audit universe, matcher, projection operator, or interpretation rules.

A canonical filtered-tuple group may contain multiple tuple-birth evidence members. The main protocol already forbids selecting whichever member gives the best cross-view match.

For diagnostics that require one concrete member window per side — specifically cross-view window-bound comparisons and the audit-only `1m_official` window projection — use the following deterministic representative:

> **earliest projection-valid member ordered by `(tuple_birth_confirmation_bar, birth_scale_level, event_id)`**.

Reasons:

1. the rule is single-view and causal;
2. it does not inspect the other view;
3. it does not inspect raw-anchor displacement, 1m results, direction, returns, or outcome;
4. all members and all distinct raw projections remain retained in the single-valuedness audit, so choosing this representative does not hide multi-valued projection identity.

If a group has no projection-valid member, it remains `no_valid_projection` / `projection_invalid_group`; no fallback member is invented.

For a `multi_valued_projection` group, the representative may be reported descriptively but the group is never collapsed to that member for cross-view raw-identity pass/fail. Cross-view status remains `within_view_multi_projection` as frozen in the main protocol.
