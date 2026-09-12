# AGENTS.md — Two-Wave repository rules

This repository is the bounded CSI1000 Two-Wave morphology/direction research lab. These rules apply to humans and coding agents working inside this repository.

## Authority hierarchy

When files disagree, resolve them in this order:

1. `experiments/two_wave_m0_authority.json` — canonical machine authority.
2. Formal experiment `RESULT.json` and `ADJUDICATION.json` files referenced by that authority.
3. Frozen protocols in `docs/research/`.
4. `docs/research/TWO_WAVE_M0_AUTHORITY.md`, `README.md`, and `docs/INDEX.md` — human mirrors/navigation.
5. Historical scripts/modules/docs — reproducibility evidence only unless a current protocol explicitly reuses them.

Never infer current authority from a versioned module name or from the newest-looking historical result.

## Current scientific boundary

As of 2026-09-12 the machine authority is `two_wave_m0_authority@1.33` with global status:

`v0708_external_validation_evidence_gap_no_candidate_opened_no_direction_winner`

Current facts that must remain explicit:

- F3 prefix-causal lifecycle/publication/qualification/direction transplantation is supported only as a Development representation chain.
- v0.6.25 is a retained non-winning Development direction contribution.
- `parent_direction.winner = null`.
- active semantic parent authority is unset.
- `morphology_acceptance = false`.
- trade and production authority are false.
- no in-sample direction challenger is authorized.

A direction-authority reopening requires BOTH genuinely new temporal evidence and new independently frozen Two-Wave morphology/reference labels. Do not substitute repeated data, same-snapshot copies, non-morphology annotations, future outcomes, or PnL.

## Data rules

### Shipped Development data

This repository ships only CSI1000 (`000852.SH`) Development bar views for `2015-01-05..2020-12-31`. Those files remain the bounded Development package and are validated byte/row-wise by `scripts/validate_theme_package.py`.

### External validation data

Post-2020 data are **not shipped here**, but external material may be consumed only under a separately frozen protocol with immutable provenance. This distinction replaces the obsolete rule that 2021+ data can never be read over the network.

Already-consumed external temporal evidence under v0.6.47 includes:

- 2024 CSI1000 1m;
- 2025 CSI1000 1m;
- 2026-01-05..2026-08-21 CSI1000 1m.

These slices are not fresh evidence anymore. v0.7.8 found no qualifying connected post-2026-08-21 minute extension and no new independent morphology/reference-label pack.

Do not copy external validation rows into the shipped Development package unless a future separately reviewed packaging change explicitly authorizes that action.

## Research discipline

- Freeze scientific object families, gates, clocks, and verdict precedence **before** reading the formal score they govern.
- Do not tune on human-reference labels, held-out temporal outcomes, future returns, PnL, trade results, or external-validation failures unless a protocol explicitly defines that data as Development information.
- Do not change qualification/direction thresholds to repair an unrelated representation/interface failure.
- Preserve causal prefix semantics. Runtime classification may not read future bars or future lifecycle state.
- Keep publication identities append-only when the relevant protocol requires it.
- A successful interface transplant is not equivalent to morphology, trading, or production authority.

## Repository organization

- `src/factor_lab/visual_structure/two_wave/` contains both current reusable Development components and historical versioned research modules. Retain historical modules needed for formal reproducibility.
- `scripts/` contains formal runners, diagnostics, and maintenance utilities. A historical runner is not a current workflow.
- `tests/` contains regression, causal-contract, replay, and governance tests.
- `experiments/` is the canonical formal result/adjudication surface. Do not redirect current formal results to the obsolete `cloud_results/` convention.
- `docs/research/` contains frozen protocols and research ledgers.
- `docs/reference/` and `docs/archive/` are frozen source/history surfaces and are non-authoritative unless a current protocol cites them.

## Workflow policy

`.github/workflows/ci.yml` is the only long-lived GitHub Actions workflow.

Formal science/governance/maintenance one-shot workflows may be created when required, but they must:

1. be narrowly path-triggered;
2. run validation/tests before writing formal state;
3. commit only the declared aggregate/governance outputs;
4. be deleted after successful closure.

Do not leave completed one-shots active in `.github/workflows/`.

## Source closure and mutable control-plane files

The original imported source closure remains byte-frozen except for explicitly designated current control-plane files in `scripts/validate_theme_package.py`. Updating a mutable authority/navigation file is not permission to rewrite historical source material.

If a broad imported index conflicts with the scoped Two-Wave index, retire the broad index as a compatibility pointer rather than treating it as current authority. Git history preserves its previous contents.

## Required validation

Before promoting a cleanup or scientific branch to `main`, run and pass:

```bash
python scripts/validate_theme_package.py
pytest -q
```

Repository consistency tests must verify at minimum:

- authority schema/global status;
- winner and runtime authority remain off when required;
- governance data declarations match actual research history;
- only the expected long-lived workflow remains;
- canonical navigation files point to the same current status.

## Main-branch policy

Research/maintenance work may occur on dedicated branches. Move `main` only by a verified fast-forward after the branch is fully closed and CI is green. Do not merge stale `main` back into a newer linear research branch merely to manufacture a merge commit.
