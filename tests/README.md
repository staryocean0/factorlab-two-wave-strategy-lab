# Tests

The test suite is part of the repository's scientific governance, not only a software-quality layer.

## Test roles

- **unit/property tests** — local mathematical and causal invariants;
- **regression tests** — historical semantics required to reproduce frozen results;
- **interface/contract tests** — lifecycle/publication/qualification/direction adapters and future-bar isolation;
- **governance tests** — authority, result/adjudication compatibility, and repository consistency.

Historical tests should be retained when they protect a formally published protocol/result. A test for an old version is not evidence that the old version remains current authority.

## Current repository-level invariants

The consistency tests and `scripts/validate_theme_package.py` must keep these synchronized:

- `two_wave_m0_authority@1.33` and the v0.7.8 global status;
- direction winner and semantic-parent authority remain unset;
- morphology/trade/production authority remain false;
- shipped Development data remain 2015–2020 only;
- consumed external validation history is recorded truthfully;
- v0.7.8 reopening remains blocked until both required external evidence types exist;
- `.github/workflows/ci.yml` remains the only long-lived workflow; any other workflow must be a temporary `*-once.yml` surface and must be retired after completion.

Run the full suite with:

```bash
pytest -q
```
