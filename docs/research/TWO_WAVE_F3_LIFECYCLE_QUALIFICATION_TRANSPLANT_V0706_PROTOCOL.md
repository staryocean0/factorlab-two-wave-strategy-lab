# Two-Wave v0.7.6 F3 Lifecycle-Publication Qualification Transplant Protocol

Date: 2026-09-12  
Status: **frozen before v0.7.6 qualification statistics**

## 1. Question

v0.7.5 established that the historical v0.6.4 sequential raw-projection and v0.6.5 first-valid immutable-publication principles can be transplanted onto the v0.7.4 prefix-causal F3 lifecycle without backdating or identity rewrite.

The next narrow question is:

> Can the already-frozen v0.5.4 full-cycle-scale qualification semantics, with the already-frozen v0.6.18 path-gate demotion policy, consume the immutable v0.7.5 lifecycle publication **as-is**, causally and without interface exceptions, while retaining enough independently anchored semantic-positive cases to justify keeping qualification as a transplantable Development component?

This is an interface + semantic-transplant precheck. It is **not** a new qualification model, threshold search, direction experiment, morphology-acceptance test, or trading study.

## 2. Frozen upstream authority

Unchanged entering v0.7.6:

- source data / clock / replay / governance;
- TCSS extrema and ridge lineage;
- F3 persistence-dominant nonconsecutive quintet as the v0.7.1 Development parent reconstruction candidate;
- v0.7.4 prefix-causal append-only lifecycle semantics;
- v0.7.5 first-observed sequential raw projection and first-valid immutable publication;
- lifecycle object key / object ID / first-observation bar / first witness;
- publication phase, five raw occurrence bars, publication confirmation bar, raw publication ID and raw pivot IDs;
- v0.5.4 numerical qualification semantics;
- v0.6.18 policy change: demote exactly `inefficient_leg` and `jump_dominated_leg` from hard vetoes to diagnostics;
- all independent reference-label files and frozen human support cells;
- no direction winner;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.

v0.7.6 may not change any of those objects or numerical thresholds.

## 3. Required v0.7.5 replication

Before qualification is interpreted, the runner must reproduce the v0.7.5 aggregate authority:

- observed lifecycle objects = **1543**;
- published lifecycle objects = **1543**;
- certified lifecycle objects = **1478**;
- certified objects published = **1478**;
- final unresolved objects = **65**;
- final unresolved objects published = **65**;
- publication delay from first observation: min = median = max = **0 bars**;
- publication hard-invariant violations = **0**;
- published-raw semantic support = **9/11** anchored human-positive cases;
- per-ordinal published-raw support-cell hit counts = **11, 11, 11, 11, 10**;
- permanent-certificate gap case count = **1**;
- same-object provisional raw support in that gap case = **1/1**.

Any drift is an implementation/lineage failure and invalidates v0.7.6 before qualification interpretation.

## 4. Frozen qualification interfaces

### 4.1 v0.5.4 control semantics

For each immutable v0.7.5 publication, call the existing published-identity qualification interface:

`qualify_published_raw_identity(phase, five_raw_occurrence_bars, publishing_confirmation_bar, bars_prefix)`

from `published_identity_qualification_v066.py`.

Its v0.5.4 hard-reason set is the existing v0.4.3 scale-rejection set with only `corresponding_leg_duration_mismatch` diagnostic-only, exactly as already frozen by v0.5.4/v0.6.6.

No threshold or measurement may be changed.

### 4.2 v0.6.18 candidate semantics

On exactly the same immutable publication and bar prefix, call:

`qualify_published_raw_identity_v0618(...)`

from `path_gate_demotion_v0618.py`.

The only allowed policy difference is:

`v0618_hard = v054_hard - {inefficient_leg, jump_dominated_leg}`.

All raw measurements and all other hard reasons remain unchanged.

## 5. Causal information boundary

Qualification must be evaluated on **exactly the observed source-bar prefix through the immutable publication confirmation bar, inclusive**.

No bar after `publishing_confirmation_bar` may be supplied to the qualification call.

A synthetic future-perturbation test must prove that appending or changing post-publication bars cannot change v0.5.4 or v0.6.18 qualification output for an already-published object.

Later C1 certification / final lifecycle state is metadata for descriptive stratification only. It may not enter qualification inputs or decide qualification.

## 6. Identity immutability

Qualification is an annotation on a frozen publication. It may not mutate:

- lifecycle object key or object ID;
- first-observation bar;
- publication phase;
- five raw occurrence bars;
- publication confirmation bar;
- raw publication ID;
- raw pivot IDs.

The runner must retain input identity hashes before and after qualification and require equality.

No qualified object may be republished, reprojected, shifted, delayed, or re-keyed.

## 7. Interface audit — primary hard gate

Every one of the **1543** v0.7.5 publications must be presented to both frozen qualification interfaces.

Required hard gates:

1. v0.5.4 interface evaluations = `1543/1543`;
2. v0.6.18 interface evaluations = `1543/1543`;
3. interface exception count = **0** for each policy;
4. identity mutation count = **0**;
5. future-bar dependency violations = **0**;
6. `future_outcome_used=false` everywhere;
7. `trade_authority=false` everywhere.

If any of these fail, semantic scoring is blocked and the verdict is an interface/implementation failure rather than a scientific rejection of qualification.

## 8. v0.6.18 semantic-contract hard gates

Across all 1543 publications:

1. every v0.6.18 hard reason must already exist in the corresponding v0.5.4 hard-reason list;
2. the set difference `v054_hard - v0618_hard` may contain only `inefficient_leg` and/or `jump_dominated_leg`;
3. no v0.5.4-qualified publication may become v0.6.18-rejected;
4. all non-demoted hard reasons must be byte-for-byte semantically unchanged;
5. raw efficiency/jump-share diagnostic values remain present and unchanged;
6. no lifecycle-state field is used by either policy.

Any violation invalidates the transplant implementation.

## 9. Label-free descriptive outputs

Before human-reference scoring, report for both v0.5.4 and v0.6.18:

- qualified count and fraction over all 1543 publications;
- hard-reason frequency table;
- number of publications changed from reject to qualified by v0.6.18;
- demoted-reason combinations responsible for each change;
- qualification by state **at publication**:
  - already C1-certified at publication;
  - unresolved at publication and later certified;
  - unresolved at publication and still unresolved at case cutoff;
- qualification by **final lifecycle state**:
  - final certified;
  - final unresolved;
- publication confirmation-delay / cycle-duration / amplitude summaries by qualification status.

These are descriptive. They do not authorize threshold adjustment.

## 10. Frozen semantic scoring universe

Only after Sections 7-8 pass may the runner use the already-frozen independent human labels.

Use the same **11 anchored human-positive cases** and the same five frozen support cells used by v0.7.0-v0.7.5.

A case is `published_raw_supported` if at least one immutable v0.7.5 publication has all five raw pivots in the five frozen human support cells with the required alternating kinds. v0.7.5 must reproduce exactly **9/11** such cases.

A case is:

- `v054_qualified_semantic_supported` if at least one `published_raw_supported` publication in that case is v0.5.4-qualified;
- `v0618_qualified_semantic_supported` if at least one `published_raw_supported` publication in that case is v0.6.18-qualified.

The object/publication used for this test must be the immutable v0.7.5 publication; no alternative later raw projection may substitute for it.

Also report per-ordinal support-cell hit counts restricted to v0.5.4-qualified and v0.6.18-qualified publications.

## 11. Pre-frozen semantic-support gate

v0.6.48 froze a candidate positive-presence calibration threshold of **80%** before human labels were unblinded. v0.7.6 reuses that already-established calibration-support standard rather than fitting a new threshold to the 11 cases.

The v0.7.5 raw-semantic-positive universe contains exactly **9** cases. Therefore a qualification transplant is semantic-supporting only if v0.6.18 preserves at least:

`ceil(0.80 * 9) = 8` raw-semantic-positive cases.

Frozen gate:

- v0.6.18 qualified semantic support >= **8 of the 9 v0.7.5 raw-semantic-positive cases**.

Equivalently, because the anchored universe contains 11 cases and v0.7.5 supports only 9 of them, the required v0.6.18 qualified semantic-support count is at least **8/11**.

v0.5.4 qualified semantic support is reported as a frozen historical-policy control, not a separate promotion gate.

The single v0.7.4 permanent-certificate gap case must be evaluated by qualification with the same immutable provisional publication. Whether it passes qualification is descriptive; it is **not** a separately fitted gate.

## 12. Frozen verdict precedence

Apply the first matching rule:

1. If required v0.7.5 replication drifts:  
   `v0706_upstream_replication_drift_invalid`.
2. Else if either qualification interface has any exception, identity mutation, future-bar dependency, or missing evaluation:  
   `v0706_qualification_interface_incompatible`.
3. Else if any v0.6.18 semantic-contract hard gate fails:  
   `v0706_v0618_qualification_contract_violation`.
4. Else if v0.6.18 qualified semantic support >= 8 of the 9 v0.7.5 raw-semantic-positive cases:  
   `v0706_v0618_lifecycle_qualification_transplant_supported`.
5. Else:  
   `v0706_qualification_interface_clean_but_semantic_support_insufficient`.

This precedence is frozen before v0.7.6 statistics.

## 13. What a pass means

A v0.7.6 support verdict means only:

- the frozen v0.5.4/v0.6.18 qualification layer can consume the v0.7.5 lifecycle publication causally and without interface repair;
- the v0.6.18 policy retains the pre-frozen 80% semantic-support standard on the v0.7.5 raw-semantic-positive anchored universe;
- v0.5.4/v0.6.18 may be retained as a Development transplant component on the reconstructed parent/publication stack.

It does **not** mean:

- morphology acceptance;
- independent fresh-OOS validation;
- direction winner selection;
- trade authority;
- production authority.

If supported, the next authorized stage may be a separately frozen direction-interface/transplant precheck on **v0.7.6-qualified immutable publications**. Direction is not evaluated in v0.7.6.

If semantic support is insufficient, the next step is a separately frozen qualification-failure attribution using the already-frozen hard reasons. Threshold fitting or further gate demotion is not automatically authorized.

## 14. Forbidden shortcuts

Do not:

- change any v0.5.4 numerical threshold;
- demote any v0.6.18 hard reason beyond `inefficient_leg` and `jump_dominated_leg`;
- wait for future C1 certification before qualifying an unresolved-at-publication object;
- condition qualification on final lifecycle state;
- use any bar after publication confirmation in qualification inputs;
- reproject or republish an object to make qualification pass;
- select a later v0.7.5 evidence realization instead of the immutable first publication;
- fit qualification thresholds or lifecycle strata using the 11 human-positive cases;
- drop the unresolved gap case;
- score D1/v0.6.25 direction;
- use future returns, PnL, H1/H2, third-wave outcome, or trading information;
- treat a v0.7.6 Development pass as active morphology authority.

## 15. Required aggregate result

Public `RESULT.json` must contain aggregate values only, including:

- upstream replication checks;
- total interface evaluation / exception counts and exception-type counts;
- identity/future-dependency invariant counts;
- v0.5.4 and v0.6.18 qualified counts/fractions;
- hard-reason aggregate counts;
- demotion-only transition counts;
- lifecycle-stratified qualification counts;
- v0.5.4 and v0.6.18 qualified semantic-support case counts;
- qualified per-ordinal support-cell hit counts;
- permanent-gap qualification status as an aggregate one-case count;
- frozen verdict and gate booleans.

Do not write case IDs, timestamps, hidden sampling mapping, case-level qualification tables, or private annotator metadata into the public result.

## 16. Execution order

1. freeze this protocol in its own commit;
2. implement qualification-transplant adapter/audit without reading aggregate qualification results;
3. add synthetic tests for prefix-only qualification, identity immutability, v0.6.18 demotion-only monotonicity, and no future-bar dependence;
4. pass bounded-theme validation + full pytest;
5. run one formal one-shot workflow;
6. commit only aggregate `RESULT.json` from the formal run;
7. adjudicate against the frozen verdict precedence;
8. synchronize machine/human authority and retain/reject downstream components accordingly;
9. remove the one-shot workflow and fast-forward `main` only after final branch CI passes.
