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

A component-level win never silently upgrades the whole recognizer. Failed challengers never erase the best existing component. Rejected versions may contribute reusable measurements or decision mechanisms.

## Current best-supported component stack

| Layer | Current best-supported component | Status |
|---|---|---|
| causal pivot / historical full recognizer | v0.4.3 temporal maturity recognizer | historical baseline; not morphology-accepted |
| parent identity | v0.5.2 exact-ridge parent identity | supported research component |
| same-scale semantics | v0.5.4 full-cycle-scale qualification | supported research component |
| raw identity publication | v0.6.5 first-valid immutable predecessor | supported research component |
| qualification policy | **v0.6.18 path-gate demotion** | **current best qualification component** |
| fine-path information measurement | v0.6.17 session-aware bounds | supported measurement capability |
| parent direction/state classification | **no winner yet** | active research layer |

## Qualification authority: v0.6.18

Formal run `34423674192`, result commit `9600eca94de9fb2cc39db4b995edec3d5e7870c3`.

It reproduced the frozen 57,029 filtered matched pairs and 29,453 published raw strict pairs. Demoting only `inefficient_leg` and `jump_dominated_leg` from hard morphology vetoes to diagnostics improved aggregate positive qualification overlap from `40.8129%` to `68.3817%` and both-qualified pairs from `482` to `1,462`, with all four offsets improving. Long-span and other safety gates remained hard.

v0.6.19 then attributed 58.14% of the remaining 676 qualification disagreements to local-duration geometry; 318/361 local-duration-only cases sat at a preregistered one-native-bar boundary. v0.6.20 proved that simply admitting exact 3-bar legs / 11-bar cycles was not a valid repair, so v0.6.18 remains unchanged.

## Direction baseline: D1

On the frozen 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified:

- exact four-state agreement: `1,400/1,462 = 95.7592%`;
- pooled decisive coverage: `48.9056%`;
- decisive agreement when both views are decisive: `100%`;
- opposite UpTrend/DownTrend conflicts: `0`.

D1 is the historical stability baseline, not human morphology truth and not a current winner. Its main defect is severe over-abstention, especially on Range.

## Direction contribution lineage

### v0.6.21 whole-window Huber

Rejected as a wholesale replacement, but proved the full completed parent window carries strong low-frequency state information:

- exact `95.7592% -> 95.0068%`;
- decisive coverage `48.9056% -> 84.2339%`;
- decisive agreement `100%`;
- opposite trend conflicts `0`.

### v0.6.22 D1-primary Huber rescue

Kept every decisive D1 output, rescued 3,737 D1-Uncertain records, and raised coverage to `85.8413%`, but exact fell to `94.7332%`. Contribution: D1-primary rescue is viable; raw rescue is too sensitive.

### v0.6.23 endpoint-erosion consensus rescue

Four fixed single-view support windows restored much of the lost stability while preserving a large coverage gain:

- exact `95.5540%`;
- decisive coverage `78.5568%`;
- decisive agreement `100%`;
- conflicts `0`.

It still failed all-offset non-regression.

### v0.6.24 residual attribution

Relative to D1: retained exact `1,350`, introduced harm `50`, repaired old nonexact `47`, persistent nonexact `15`. Every introduced-harm pair began as D1=`Uncertain` on both sides and had a one-sided rescue. This supported a single margin gate.

### v0.6.25 absolute-margin rescue — strongest pooled-exact contribution

Formal run `34447731074`, result commit `ea103714043ac5fbac4c0ae6d806377fb5cf76a9`.

With frozen consensus margin `>=0.10` amplitude units:

- exact **`1,402/1,462 = 95.8960%`**, above D1;
- decisive coverage **`70.8618%`**;
- decisive agreement `100%`;
- conflicts `0`;
- per-offset exact counts `380 / 271 / 292 / 459`.

It was rejected because offsets 1 and 2 regressed and Range almost disappeared: only 22 pooled decisive Range labels, 1.0618% of decisive labels. It remains the strongest pooled-exact contribution, not a direction winner.

### v0.6.26 state-asymmetry attribution

Confirmed that a common absolute margin is structurally asymmetric: it retains most trend rescues but nearly eliminates Range. This authorized a state-relative Range confidence experiment, not generic threshold tuning.

### v0.6.27 state-relative margin rescue

Used the frozen 20% relative geometry: trend absolute margin `0.10`, Range absolute margin `0.03`. It restored meaningful Range/class diversity but reduced pooled exact to `94.9384%` and generated too many one-sided Range rescues. Rejected; Range-relative margin remains a useful contribution.

### v0.6.28 Range-rescue attribution

v0.6.25 -> v0.6.27 transitions were retained exact `1,383`, introduced harm `19`, repaired v0.6.25 nonexact `5`, persistent nonexact `55`. All changes were `Uncertain -> Range`. Although support dispersion differed between harmful and successful Range rescues, the harmful group had only 19 cases versus the frozen minimum 20, so **no support-dispersion threshold is authorized from v0.6.28**.

### v0.6.29 cycle-band Range rescue

Formal run `34492604772`, result commit `7fff2c6ad6daad3e63c3ef942828655de1f7812f`.

This preserved v0.6.25 and added Range only when the two complete cycles' robust central IQR occupancy bands overlapped by at least 50%. The 50% threshold was a preregistered geometric definition, not fitted post hoc.

Results:

- exact `95.8960% -> 95.4172%`;
- decisive coverage `70.8618% -> 75.0684%`;
- Range share among decisive labels `1.0618% -> 6.6059%`;
- decisive agreement `100%`;
- opposite trend conflicts `0`;
- D1 decisive overrides `0`;
- 337 new Range rescues across all single-view publications;
- every label change was exactly `Uncertain -> Range`.

Per-offset exact delta versus v0.6.25 was `-0.50 / -0.70 / -0.99 / 0.00 pp`, so the candidate was rejected. Retained contribution: **two-cycle robust price-band overlap is an independent and meaningful Range signal, but overlap alone is too permissive for cross-slicing stability**.

## Current direction research rule

The parent-direction winner is still **unset**. Keep v0.6.25 as the strongest pooled-exact contribution until a preregistered candidate passes every gate.

Rejected routes must not be silently retried: endpoint D2, confidence-gated endpoint D2, PAWCT as previously adjudicated, wholesale Huber replacement, unconditional Huber rescue, ungated erosion-consensus rescue, post-hoc retuning of v0.6.25 margin, v0.6.27 direct state-relative Range admission, v0.6.28 fitted support-dispersion gate, and v0.6.29 cycle-band overlap used alone.

## Next authorized step

Preregister one direct v0.6.30 intersection candidate:

- preserve every v0.6.25 decisive output exactly;
- only consider records still `Uncertain` under v0.6.25;
- require v0.6.23 erosion consensus = `Range`;
- require the already-frozen v0.6.27 Range absolute margin `>=0.03`;
- require the already-frozen v0.6.29 cycle-IQR overlap `>=0.50`;
- only then rescue to `Range`.

Neither threshold may be tuned in v0.6.30. Qualification stays v0.6.18. Cross-offset information remains evaluation-only. No future return, PnL, H1/H2, third wave, 2021+, or 2026 data may be used for morphology selection.

Independent morphology acceptance remains false. Trading and production remain closed.
