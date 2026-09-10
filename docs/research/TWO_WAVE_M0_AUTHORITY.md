# Two-Wave M0 Authority

Date: 2026-09-10

## Global scientific status

- Primary object: `two_wave_parent_structure_recognizer`.
- Target semantics: two complete same-scale waves -> parent `Range / UpTrend / DownTrend / Uncertain`.
- Independent morphology acceptance: **false**.
- Global status: `morphology_replication_not_yet_accepted`.
- Historical full-recognizer operational baseline: **v0.4.3**.
- Trade authority: **false**.
- Production authority: **false**.

A later component may be better supported without changing the full-recognizer baseline. Failed challengers never erase the current best component, and a component-level win never silently upgrades the whole recognizer. A rejected challenger may still contribute a reusable measurement or decision mechanism.

## Current best-supported component stack

| Layer | Current best-supported component | Status | Meaning |
|---|---|---|---|
| causal pivot / original full recognizer | v0.4.3 temporal maturity recognizer | historical operational baseline | last full recognizer baseline; not morphology-accepted |
| parent identity | v0.5.2 exact-ridge parent identity | supported research component | causally absorbs child-scale extrema and recovers parent five-anchor identity |
| same-scale qualification semantics | v0.5.4 full-cycle-scale qualification | supported research component | corresponding half-leg duration mismatch is diagnostic, not a hard same-scale veto |
| raw financial identity publication | v0.6.5 first-valid immutable predecessor publication | supported research component | one canonical filtered identity publishes at most one append-only raw identity |
| qualification policy | **v0.6.18 path-gate demotion** | **current best research qualification component** | resolution-sensitive `inefficient_leg` and `jump_dominated_leg` are diagnostics, not hard morphology vetoes |
| fine-path information measurement | v0.6.17 session-aware bounds | cloud-reviewed measurement capability | carries partial-identification intervals where native 5m does not identify fine path |
| parent direction/state classification | **no current winner** | active research layer | D1 remains the historical cross-slicing stability baseline; v0.6.21/22/23/25 are rejected contributors |

## Qualification authority remains v0.6.18

Formal run: `34423674192`. Formal result commit: `9600eca94de9fb2cc39db4b995edec3d5e7870c3`.

Frozen controls reproduced exactly: filtered mutual-unique pairs `57,029`, published raw strict pairs `29,453`, and the v0.6.6 control matrix. After demoting only the two resolution-sensitive path reasons, aggregate positive qualification overlap improved `40.8129% -> 68.3817%` and both-qualified increased `482 -> 1,462`; all four offsets improved and the long-span safety gates remained hard.

v0.6.19 then showed that `393/676 = 58.14%` of remaining qualification disagreements involved local duration, with `318/361 = 88.09%` of local-duration-only disagreements at preregistered one-native-bar boundaries. v0.6.20 proved that simply admitting exact 3-bar legs / 11-bar cycles was not a valid repair: supply rose but cross-slicing positive stability fell. Therefore v0.6.18 remains qualification champion unchanged.

## Historical direction baseline: D1

On the frozen v0.6.18 both-qualified same-financial-identity universe of `1,462` pairs:

- exact four-state agreement: `1,400/1,462 = 95.7592%`;
- decisive coverage: `48.9056%`;
- decisive agreement when both views are decisive: `100%`;
- opposite UpTrend/DownTrend conflicts: `0`.

D1 is therefore a strong stability baseline but materially over-abstains, especially on Range. It is not human morphology truth and is not a current direction winner.

## v0.6.21: whole-window Huber — rejected, contribution retained

Formal result commit `4fe8e4d837bcb5d9accb372c0bc754be137ff0a1`; primary run `34439356292`.

- exact agreement `95.7592% -> 95.0068%`;
- decisive coverage `48.9056% -> 84.2339%`;
- decisive agreement `100%`;
- opposite trend conflicts `0`;
- pooled Range labels `9 -> 254`.

It failed as a wholesale replacement, but proved that the completed whole-parent window contains strong low-frequency state information. That information should be used conservatively as a rescue signal.

## v0.6.22: D1-primary Huber rescue — rejected, contribution retained

Formal run `34440036520`; result commit `89126f20a17be5e8b64c296cff4a5795efb371c4`.

D1 decisive overrides were exactly zero. The candidate rescued `3,737` D1-Uncertain records and raised decisive coverage to `85.8413%`, but pooled exact agreement fell to `94.7332%`. This established that D1-primary rescue is viable, but raw Huber rescue is too sensitive at the rescue/abstention boundary.

## v0.6.23: endpoint-erosion-consensus rescue — rejected, contribution retained

Formal run `34442468065`; result commit `a8ca442ccb7482164c2dd3cdeee8b8640ea40957`.

Using four fixed single-view support windows (full, left-eroded-1, right-eroded-1, both-eroded-1) and requiring unanimous decisive Huber state recovered most of v0.6.22's stability loss:

- pooled exact agreement: `95.5540%`, only `-0.2052 pp` versus D1;
- decisive coverage: `78.5568%`, `+29.6512 pp` versus D1;
- decisive agreement: `100%`;
- opposite trend conflicts: `0`;
- D1 decisive overrides: `0`.

It still failed because offset1 and offset3 regressed. Endpoint erosion is therefore retained as a useful stability mechanism, not a direction winner.

## v0.6.24: residual attribution — diagnostic evidence

Formal result commit `347812dd269aa34ff7520c181d94b4c5f92badd6`.

No recognizer rule changed. Relative to D1, the 1,462 pairs decomposed into:

- retained exact: `1,350`;
- introduced harm: `50`;
- repaired old nonexact: `47`;
- persistent nonexact: `15`.

Every introduced-harm pair started with D1=`Uncertain` on both slicing views and had exactly one side rescued (`28` main-only, `22` other-only). The already-defined single-view consensus margin to the frozen Huber boundary strongly separated many harmful and useful rescues:

- introduced harm median `0.02786`, p90 `0.08200`;
- repaired old nonexact median `0.28769`, p25 `0.12734`.

This supported testing one preregistered margin gate, not a threshold search.

## v0.6.25: margin-gated erosion-consensus rescue — rejected, major contribution retained

Formal run `34447731074`; formal result commit `ea103714043ac5fbac4c0ae6d806377fb5cf76a9`.

The only new rule was `consensus_margin >= 0.10` amplitude units. No grid or offset-specific tuning was used. A floating-point implementation bug at exact equality was corrected only with machine epsilon; the frozen `0.10` boundary itself did not change.

Results:

- D1 exact: `1,400/1,462 = 95.7592%`;
- v0.6.23 exact control: `1,397/1,462 = 95.5540%`;
- **v0.6.25 exact: `1,402/1,462 = 95.8960%`**, now above D1 pooled;
- decisive coverage: **`70.8618%`**, still `+21.9562 pp` over D1;
- decisive agreement: `100%`;
- opposite UpTrend/DownTrend conflicts: `0`;
- D1 decisive overrides: `0`;
- v0.6.23 rescues: `3,055`; v0.6.25 rescues: `2,367`; margin-withheld: `688`.

Per-offset exact deltas versus D1 were `-0.50 / -0.35 / +0.33 / +0.85 pp`, so the all-offset non-regression gate failed. The decisive class-diversity gate also failed: pooled decisive Range share was only `1.0618%` (22 Range labels), below the frozen `2%` floor.

Formal verdict: `v0625_D1_primary_erosion_consensus_margin_rescue_direction_rejected`.

Retained contribution: **margin gating is real progress**. It moved pooled exact agreement above D1 while preserving a large coverage gain, perfect decisive agreement and zero opposite-trend conflicts. But a common absolute `0.10` margin is structurally asymmetric: a Range score can have at most `0.15` margin to its boundary, while trend margin is unbounded above `0.50`. The current evidence therefore does not authorize simply tuning another threshold. It authorizes diagnosis of residual offset harm and Range-vs-Trend confidence geometry.

## Contribution rule

A rejected version is not equivalent to no progress. For every challenger, retain separately:

1. whole-version promotion result;
2. validated local contribution;
3. failure cost / boundary;
4. whether the contribution is authorized for a later challenger.

The current best component remains unchanged until a preregistered promotion gate passes.

## Rejected routes that must not be silently retried

- v0.4.4 fixed 12-48 hierarchy;
- endpoint D2 and confidence-gated endpoint D2;
- PAWCT as previously adjudicated;
- shared-1m with frozen 5m thresholds;
- direct native-OHLC concentration proxies;
- v0.6.20 direct one-bar duration relaxation;
- v0.6.21 wholesale Huber replacement;
- v0.6.22 unconditional Huber rescue;
- v0.6.23 ungated erosion-consensus rescue as a winner;
- changing the v0.6.25 `0.10` threshold post hoc inside the same version.

## Next authorized research step

Before any new direction threshold or candidate, perform **v0.6.26 residual diagnostic decomposition** of v0.6.25:

1. reproduce the frozen v0.6.18 universe, D1 controls, v0.6.23 control, and v0.6.25 result exactly;
2. decompose v0.6.25 nonexact pairs by offset and D1 transition (`retained_exact / introduced_harm / repaired_old_nonexact / persistent_nonexact`);
3. separate one-sided versus two-sided rescues;
4. separate rescue state (`Range / UpTrend / DownTrend`);
5. quantify v0.6.23 rescue margins that v0.6.25 kept versus withheld, especially Range versus Trend;
6. report state-relative margin geometry only as a diagnostic; do not change any runtime rule.

Only after this attribution may a new v0.6.27 direction challenger be preregistered. Cross-offset data remains evaluation-only and may never become a runtime feature. No future return, PnL, H1/H2, third wave, 2021+, or 2026 data may be used for morphology selection.

Independent morphology acceptance remains false. Trading and production remain frozen.
