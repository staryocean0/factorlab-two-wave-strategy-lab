# DataHub bar-support provenance acquisition status — 2026-09-07

Status: **AUTHORITATIVE EXTERNAL DEPENDENCY UNAVAILABLE ON CURRENT SURFACES**

Research branch: `codex/two-wave-phase1-20260905`

Global research state remains `morphology_replication_not_yet_accepted`; operational baseline remains **v0.4.3**. This is an operations/provenance record, not a new morphology version and not a data-contract substitution.

## Trigger

v0.6.16 formally adjudicated:

`bar_support_contract_not_recoverable_from_available_artifacts`

The FactorLab source chain states that wall-clock offset bars are constructed by the project **DataHub**, and points the product truth source to:

`../../unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`

The current five 5m artifacts declare `data_contract = cn_a_session_wall_clock_offset_v1`, but their per-row `source_minute_count` is null and they do not expose exact `support_start/support_end` or source-row provenance. Therefore deterministic hidden-path bounds cannot legally proceed from the current artifacts alone.

## Acquisition attempts completed in this Chat session

### 1. Linked GitHub installation

Searched the connected GitHub installation for repository/project name `unified_datahub`, including the available pagination. No matching accessible repository was returned.

Result: **project DataHub repository is not accessible through the current GitHub connection**.

### 2. Public GitHub repository visibility

Searched public GitHub for `unified_datahub` under owner `staryocean0`. No visible repository was returned.

Result: **no public project repository was found**.

Unrelated public repositories/projects using the generic name "DataHub" were not used as substitutes.

### 3. Public web discovery

Searched exact/near-exact strings for:

- `session-offset-bars-whitepaper.md`
- `cn_a_session_wall_clock_offset_v1`
- project `unified_datahub`

No authoritative project document was found. Results referring to unrelated DataHub software/projects were rejected.

### 4. FactorLab repository / uploaded archive

Searched the available FactorLab branch/archive for DataHub bar-construction source. FactorLab contains references/workflows/whitepapers that point **outward** to the DataHub truth source, including timing/session-offset documentation, but does not vendor the authoritative `unified_datahub` implementation or `session-offset-bars-whitepaper.md` contract.

Result: **FactorLab supplies the dependency pointer, not the missing authority**.

### 5. ChatGPT File Library

Searched the user's File Library for prior uploads containing `unified_datahub`, `session-offset-bars-whitepaper`, `cn_a_session_wall_clock_offset_v1`, or provenance-rich session-offset exports. No relevant authoritative repository/archive/contract/export was found.

### 6. Current frozen artifacts

v0.6.16 already established that the frozen 5m products are provenance-incomplete for this purpose:

- `source_minute_count` is null on all rows of all five 5m products;
- no exact `support_start/support_end` fields;
- no source-row IDs/source timestamp lists.

Empirical `H_end_5` agreement remains **plausibility/falsification evidence only**. It is not promoted to a product contract.

## Recheck after repository advanced to v0.6.16

A second autonomous recheck was completed on 2026-09-07 after the research branch had already advanced beyond v0.6.13:

- linked-installation search for `unified_datahub`: no result;
- linked-installation search for generic `datahub`: no result;
- owner-level enumeration for `staryocean0`: only the currently accessible FactorLab-related repositories were returned; no renamed DataHub candidate exists in the accessible owner surface;
- public `staryocean0` repository search for `unified_datahub`: no result;
- File Library exact-term recheck: no authoritative DataHub archive/contract/provenance-rich export found;
- current repository issue search: no pre-existing unblock issue.

The dependency has therefore been converted into tracked GitHub issue **#4 — `Unblock morphology research: provide authoritative DataHub 5m bar-support provenance`**.

Issue #4 is the operational unblock surface. Closing it requires one of the minimum evidence conditions below; closing it without supplying authoritative provenance is not sufficient.

## Final acquisition status

`authoritative_datahub_bar_support_evidence_unavailable_in_current_surfaces`

All currently available autonomous evidence channels have been checked. Further algorithmic iteration on guarantee-style hidden-path bounds is **blocked by provenance**, not by a missing proxy formula.

## Minimum unlock condition

Any one of the following is sufficient to reopen the bounds workstream:

1. Connect/authorize the actual project `unified_datahub` repository so the assistant can read at minimum:
   - `docs/modules/history/session-offset-bars-whitepaper.md`, and preferably the corresponding bar-construction implementation/tests; or
2. Upload/provide an archive or copy of the authoritative DataHub contract/implementation; or
3. Provide a DataHub provenance-rich re-export of the relevant 5m products in which each bar includes at minimum:
   - `source_minute_count`;
   - exact `support_start`;
   - exact `support_end`;
   - preferably source-row IDs and/or exact source timestamps.

## Explicitly prohibited while blocked

Until one unlock condition is satisfied, do **not**:

- freeze `H_end_5` as authoritative support truth;
- locally resample `1m_official` to redefine 5m support;
- discard lunch/overnight/session-boundary legs and continue deterministic bounds on the remainder;
- infer guarantee-style hidden-path bounds from adjacent native closes;
- revert to point-estimate concentration proxies as a substitute for provenance;
- resume direction, third-wave, outcome/P&L, fresh OOS, paper trading or production.

## Resume rule

Once authoritative support provenance becomes available, the next action is a **new results-blind session-aware information-set bounds preanalysis/protocol** that consumes the recovered contract/provenance. No prior H_end_5 best-fit relation is grandfathered in as truth.
