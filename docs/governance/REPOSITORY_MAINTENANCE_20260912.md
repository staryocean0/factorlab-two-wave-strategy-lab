# Repository reconciliation — 2026-09-12

This is maintenance, not a new scientific experiment. The scientific endpoint remains v0.7.8.

## Input and findings

Input commit: `ec0d49f1cec7d6c34d13af0fcfdb824687d57392`; tree: `9679ee00f5aa063b2208e597e590d1a70edaa917`. The starting main was v0.7.6 (`ef29291535bc0fc239269ee9cb7c8e5a8512418c`).
v0.7.7/v0.7.8 adjudications existed on research branches but had not reached main.
README, INDEX, the human authority, AI entry and cloud-environment instructions had stale or contradictory current-state descriptions.
The initial scan found 4526 missing Markdown local-file targets in 49 imported documents; 524 Python files parsed without syntax errors.
Three large document pairs were byte-identical duplicates.

## Disposition

All 871 original files have a SHA256-preserved copy or remain byte-identical in place.
89 imported document entries now explicitly redirect to archived originals; 4 automatic strategy-skill files are removed from the discovery path.
105 unique archive copies preserve affected originals. Duplicate document payloads share an archive destination instead of being copied twice.
All market data, labels, scientific protocols, implementation modules, historical positive/negative results and original tests are unchanged.
The old v0.7.7 governance CLI is retired and cannot roll current authority back; pure historical helpers remain testable.
Frozen source verification follows explicit archive paths and still checks the original source digests; the immutable source manifest is not rewritten.

## Current organization

[Current entry](../../CONTINUE_HERE.md), [whitepaper](../research/TWO_WAVE_WHITEPAPER.md),
[authority](../../experiments/two_wave_m0_authority.json), [component inventory](repository_component_inventory.json),
[preservation map](repository_preservation_manifest_20260912.json), [archive policy](../../archive/README.md).
Archived relative links retain their original upstream context and are not claimed to be runnable package links.
All non-archived Markdown local-file links are checked, and all files receive an explicit component status.
Only the read-only bounded-theme-validation CI is allowed in the final working tree; no scientific one-shot remains active.

## Actual execution boundary

The session container could not resolve github.com for git clone. The authorized GitHub snapshot export supplied the exact input tree.
Local static checking is available; local Python is 3.13 and lacks pyarrow, so it is not the declared Python-3.11/full-data test environment.
Local maintenance tests and the standard-library validator are executed separately. Full package/data validation and the full regression suite use GitHub Actions Python 3.11.
The final execution receipt is written only after commands actually return success; this document is not itself a green-CI certificate.
Repository visibility was already public; this maintenance does not change visibility, copy private data into it, or claim a new privacy authorization.
