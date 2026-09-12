# Repository Consistency Refresh — 2026-09-12

## Purpose

Bring the repository's documentation, authority records, code/test navigation, governance declarations, and workflow surface into one truthful current state after the v0.7.x semantic-parent reconstruction/transplant sequence.

This maintenance action does **not** alter scientific thresholds, replay results, human labels, direction classifications, or formal experiment verdicts.

## Pre-refresh inconsistencies found

1. `main` lagged the completed v0.7.7/v0.7.8 line even though the research branches were a pure fast-forward continuation.
2. Root `README.md`, `docs/INDEX.md`, and `docs/research/TWO_WAVE_M0_AUTHORITY.md` contained older v0.5/v0.6 current-state language plus later appended v0.7 updates.
3. `AGENTS.md` still prohibited all 2021+ external reads and routed formal results to an obsolete `cloud_results/` convention, inconsistent with the frozen v0.6.47 external-validation history and current `experiments/` surface.
4. `ai-readme.md`, `docs/00-index.md`, `docs/ops/README.md`, and `docs/user/README.md` were broad imported FactorLab/REAKA indexes that could be mistaken for current Two-Wave authority.
5. `package_scope.json` incorrectly required a private repository although the repository is public.
6. `data_usage_declaration.json` claimed 2021–2026 data had not been read, although v0.6.47 had formally consumed external 2024/2025/2026 temporal slices under a frozen protocol.
7. The package validator checked frozen source/data integrity but did not check current scientific/governance consistency.
8. Code, runner, and test directories lacked explicit current-vs-historical role documentation.

## Maintenance decisions

### Retained

- Historical v0.5.x/v0.6.x/v0.7.x implementation modules required for reproducibility.
- Historical formal runners required to reproduce frozen results.
- Historical tests protecting published semantics.
- All formal experiment RESULT/RESULT_CARD/ADJUDICATION records.
- Frozen imported/reference/archive documents.

### Retired as current guidance

- Broad parent-project contents of `ai-readme.md` and `docs/00-index.md`.
- Broad parent-project navigation in `docs/ops/README.md` and `docs/user/README.md`.

Their old contents remain recoverable from Git history; the files now act as scoped Two-Wave entry points or compatibility pointers.

### Workflow cleanup

All completed science/governance/maintenance one-shot workflows are removed after use. `.github/workflows/ci.yml` is the sole long-lived workflow. Future temporary workflows must be narrowly triggered `*-once.yml` surfaces and must be retired after closure.

## New current-control guarantees

- Machine authority: `two_wave_m0_authority@1.33`
- Global status: `v0708_external_validation_evidence_gap_no_candidate_opened_no_direction_winner`
- Repository component status: `docs/governance/repository_component_status.json`
- Package scope: `two_wave_cloud_theme_package_scope@1.1`
- Data usage: `two_wave_cloud_theme_data_usage@1.1`
- Current control-plane validation is part of `scripts/validate_theme_package.py`.
- CI and unit tests verify authority, data declaration, navigation status, and workflow boundaries.

## Scientific invariants preserved

- v0.7.7 formal run/result remains unchanged.
- v0.6.25 remains a non-winning Development contribution with 19 publication-level rescues.
- D1 and v0.6.25 remain tied on the frozen supported case-level semantic subset (`7/9` exact each).
- v0.6.47 temporal replication weakness remains binding.
- v0.6.48 independent-reference weakness remains binding.
- no semantic-parent authority, direction winner, morphology acceptance, trade authority, or production authority is granted.
- v0.7.8 remains a no-candidate evidence-availability closure.

## Final promotion rule

The cleanup branch may replace `main` only by a non-forced fast-forward after full package validation and `pytest -q` pass on the final repository state.
