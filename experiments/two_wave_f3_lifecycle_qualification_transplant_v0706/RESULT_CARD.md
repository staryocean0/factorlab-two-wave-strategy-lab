# Two-Wave v0.7.6 F3 lifecycle qualification transplant — result card

Date: 2026-09-12  
Status: **supported as a Development qualification transplant; not active morphology authority**

## Frozen protocol

- Protocol: `docs/research/TWO_WAVE_F3_LIFECYCLE_QUALIFICATION_TRANSPLANT_V0706_PROTOCOL.md`
- Protocol freeze commit: `174188e55f573f43c7dac0e2d5d87f9a223bebaf`
- Authoritative formal workflow run: `34687608997`
- Authoritative result commit: `cc5942b074fd42ffdc10f78508688e21a451bc06`
- Result: `experiments/two_wave_f3_lifecycle_qualification_transplant_v0706/RESULT.json`

## Formal verdict

`v0706_v0618_lifecycle_qualification_transplant_supported`

All preregistered gates passed. This supports transplantation of the frozen v0.5.4 / v0.6.18 published-raw qualification semantics onto immutable v0.7.5 F3 lifecycle publications. It does **not** grant active morphology authority, a parent-direction winner, trade authority, or production authority.

## Upstream replication

The v0.7.5 lifecycle/publication authority reproduced exactly on the frozen 11-case anchored universe:

- observed lifecycle objects: `1543`
- published lifecycle objects: `1543`
- certified lifecycle objects: `1478`
- certified publications: `1478`
- final-unresolved lifecycle objects: `65`
- final-unresolved publications: `65`
- publication delay min / median / max: `0 / 0 / 0` bars
- publication hard-invariant violations: `0`
- published raw semantic support: `9/11`
- published raw per-ordinal cell hits: `11/11, 11/11, 11/11, 11/11, 10/11`
- permanent-certificate gap cases: `1`
- same-object provisional raw support for that gap: `1/1`

## Qualification interface audit

Both historical qualification policies were evaluated on every immutable lifecycle publication using only the causal prefix ending at the publication confirmation bar:

- v0.5.4 evaluated: `1543/1543`
- v0.6.18 evaluated: `1543/1543`
- v0.5.4 exceptions: `0`
- v0.6.18 exceptions: `0`
- publication-identity mutations: `0`
- future-bar dependency violations: `0`
- future-outcome / trade-authority violations: `0`

The interface gate passed.

## Frozen v0.6.18 contract audit

The v0.6.18 transplant reproduced the registered policy exactly:

`v0618_hard = v054_hard - {inefficient_leg, jump_dominated_leg}`

- contract violations: `0`
- v0.5.4 qualified: `42 / 1543` (`2.72%`)
- v0.6.18 qualified: `115 / 1543` (`7.45%`)
- v0.5.4 reject -> v0.6.18 qualified transitions: `73`
  - `inefficient_leg` only: `47`
  - `jump_dominated_leg` only: `14`
  - both registered path reasons: `12`
- no third hard reason was demoted
- no threshold changed

Lifecycle strata under v0.6.18:

- already certified at publication: `35 / 809` qualified
- unresolved at publication, later certified: `71 / 669` qualified
- unresolved at publication, still unresolved: `9 / 65` qualified
- final certified: `106 / 1478` qualified
- final unresolved: `9 / 65` qualified

These strata are descriptive only. Final certification was not used to qualify an object.

## Frozen semantic transplant gate

Human support cells were opened only after the label-free interface and contract gates were clean.

- published raw semantic support: `9/11`
- v0.5.4-qualified semantic support: `3/11`
- v0.6.18-qualified semantic support: `9/11`
- preregistered v0.6.18 semantic support gate: at least `8/9` of the nine published-raw-supported cases
- gate result: **pass**
- v0.6.18-qualified per-ordinal cell hits: `9/11, 10/11, 10/11, 10/11, 10/11`
- final-unresolved v0.6.18-qualified raw support: `1`
- permanent-certificate gap same-object v0.6.18-qualified raw support: `1/1`

## Implementation-invalid lineage retained

The authoritative result is the retry2 run above. Two earlier execution attempts remain explicitly non-authoritative:

1. Formal run `34685420204`, result commit `f3f47f115faf54fb688dcb26a86998b6daa49169`, was implementation-invalid because the aggregate runner iterated the keys of the ordinal-count mapping and serialized `[0,1,2,3,4]` instead of the frozen values `[11,11,11,11,10]`. The same run had already passed the qualification interface, v0.6.18 contract, and semantic gates; the invalid verdict was caused solely by this aggregate serialization error.
2. Retry run `34687496456` failed before scientific execution with a CLI import-path error (`ModuleNotFoundError: scripts`). It produced no replacement scientific result.

The retry adapter changed only ordinal-count representation / command-line import plumbing. The frozen protocol, qualification thresholds, decision precedence, lifecycle/publication identity, and semantic gates were unchanged.

## Authority consequence

v0.6.18 is now supported as a **Development lifecycle-publication qualification transplant** on top of the v0.7.5 representation. This is not full morphology acceptance and does not by itself reactivate historical direction authority.

The next admissible stage is a separately frozen lifecycle-qualified direction transplant/adjudication. It must preserve v0.7.6 qualification and v0.7.5 publication/lifecycle identity, use D1 as the historical baseline and v0.6.25 only as a retained historical challenger/contribution, prohibit threshold retuning, enforce zero D1-decisive override, and only then score frozen human direction semantics. The prior v0.6.47 temporal-replication weakness and v0.6.48 reference-calibration weakness remain constraints and cannot be erased by a Development direction replay.

`morphology_acceptance=false`; `trade_authority=false`; `production_authority=false`.
