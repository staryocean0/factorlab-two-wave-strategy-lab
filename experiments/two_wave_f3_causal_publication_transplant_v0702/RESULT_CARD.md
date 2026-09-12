# v0.7.2 F3 Causal Event / Publication + Downstream Transplant Precheck — Result Card

Formal workflow run: `34679691056`  
Protocol: `docs/research/TWO_WAVE_F3_CAUSAL_PUBLICATION_TRANSPLANT_V0702_PROTOCOL.md`  
Protocol freeze commit: `9b062153bd28b9591b66eb26fcebf8f1d431a24f`  
Formal result commit: `291633b7063e16acc7f39f261cefb1ff175d4cfb`

## Purpose

v0.7.1 retained `F3 = persistence-dominant nonconsecutive quintet` as a Development semantic-parent reconstruction candidate. v0.7.2 asked, without reading any human labels or packet strata, whether F3 can be given an immutable causal event certificate and whether that alone identifies one publishable parent object per cutoff.

Primary audit universe: all `240` frozen v0.6.48 packet cutoffs, treated only as a committed set of 96-bar historical windows.

## Frozen controls

- source SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`
- sampling commitment: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`
- human reference labels used: **false**
- packet stratum used: **false**
- future outcome / PnL used: **false**
- F3 definition changed: **false**
- threshold fitting: **false**

## Gate A — immutable causal event certificate

Ordinary F3 population across the 240 cutoffs:

- F3-positive cutoffs: `240/240`
- total ordinary final-cutoff F3 objects: `34,029`
- ordinary object count per cutoff: median `137`, Q1 `114`, Q3 `167`, range `32..267`

Death-certified F3:

- certified objects: `31,324 / 34,029 = 92.0509%`
- cutoffs with at least one certified object: `240/240 = 100%`
- certificate replay failures: `0`

Certificate delay from the selected base realization:

- median `0` bars
- Q1 `0`
- Q3 `4`
- maximum `56`

Certificate mechanism:

- `20,376 / 31,324 = 65.0492%` require explicit skipped-ridge death witnesses;
- `10,948 / 31,324 = 34.9508%` certify immediately with no skipped ridge.

The preregistered Gate A required both object coverage and cutoff-presence coverage `>=80%` plus zero replay failures. **Gate A passes.**

## Gate B — direct single-parent publication identifiability

Certified F3 object multiplicity per F3-positive cutoff:

- median: **125**
- Q1: `105`
- Q3: **152.25**
- range: `32..245`

The preregistered direct-publication band required median `<=1` and Q3 `<=2`. **Gate B fails decisively.**

## Formal verdict

**`v0702_f3_immutable_event_certificate_supported_append_only_concept_salvaged_object_selection_unresolved`**

The counteroffensive therefore salvages another historical result:

- the v0.6.5 **append-only publication concept** — publish only after an immutable causal object certificate and never rewrite that same object identity — is structurally reusable for F3;
- the exact v0.6.5 legacy grouping/function is not directly reusable because F3 identity differs;
- causal event timing itself is no longer the blocker.

The remaining blocker is **structural parent selection / uniqueness**: F3 defines a large set of causally legitimate parent candidates at every audited cutoff.

## Downstream transplantation status

- v0.6.5 append-only publication concept: **salvaged / eligible for transplantation**.
- v0.6.4 predecessor raw projection unchanged: **not directly transplantable**, because its implementation requires five consecutive birth-level nodes while F3 is nonconsecutive.
- sequential raw-projection idea: **not declared false**; it requires a separately frozen generalized F3 projection contract after one parent identity can be selected structurally.
- v0.6.6/v0.6.18 qualification interface: **structurally eligible later** once a deterministic F3 raw projection exists; thresholds not revalidated here.
- D1/v0.6.25: **historical components retained; transplantation not yet opened**.

## Next authorized step

Freeze a **purely structural F3 object-selection / uniqueness audit**.

It must operate without human-reference proximity and without fitted amplitude/duration/distance thresholds. Its first job is to determine whether existing ridge topology, persistence, causal certification time, nesting/dominance, or other already available structural order can collapse the median `125` certified candidates toward one parent object without destroying the semantic support recovered in v0.7.1.

Only after a deterministic parent-selection rule is frozen may generalized F3 raw projection be opened.

`morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.
