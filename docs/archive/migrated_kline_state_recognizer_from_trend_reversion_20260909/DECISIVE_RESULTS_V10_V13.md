# Decisive migrated results — historical K-line recognizer v10-v13

Source repository: `factorlab-trend-reversion-regime-lab`.
These are supporting state-classification results, not Two-Wave morphology acceptance.

## v10 — temporal blend

Historical promotion inside the source recognizer lineage: **passed**.

Selected: six-bar temporal auxiliary, `alpha=0.30`, auxiliary `C=0.1`, with the v5 primary head/decoder retained.

Pre-2025 worst-cell:

- balanced accuracy `0.7553851080`;
- macro F1 `0.7591912321`;
- transition F1 `0.1984334204`;
- max false transitions/day `1.2066115702`.

Consumed 2025 diagnostic:

- CSI1000: BA `0.8143`, Macro F1 `0.8105`, Transition F1 `0.2314`, false/day `1.0905`;
- STAR50: BA `0.7893`, Macro F1 `0.7908`, Transition F1 `0.2198`, false/day `1.0165`.

Historical result commit: `723404633fccb0a52181d2090cadbca3114dcc67`.

## v11 — higher temporal blend weight

Promotion: **failed**.

Best `alpha=0.45`:

- BA `0.7575591438`;
- Macro F1 `0.7617585588`;
- Transition F1 `0.2010582011`;
- max false/day `1.1652892562`.

All four aggregates moved favorably, but not enough to satisfy the frozen material-improvement gate.

## v12 — soft Shock-exit inertia

Promotion: **failed**.

Best `gamma=0.10`:

- BA `0.7555505391`;
- Macro F1 `0.7592463437`;
- Transition F1 `0.1989528796`;
- max false/day `1.1942148760`.

The v6 transition-asymmetry contribution was revalidated as a small effect, but not enough to replace v10.

## v13 — low-weight persistence prior

Promotion: **failed**.

Best `rho=0.05`:

- BA about `0.757`;
- Macro F1 about `0.761`;
- Transition F1 about `0.199`;
- max false/day `1.231`.

Point-state/transition F1 improved slightly, but churn worsened versus v10, so v10 remained the historical source-line winner.

## Two-Wave boundary

None of the versions above proves two-complete-wave morphology replication. They may inform baselines, temporal features, persistence priors and transition governance only after the Two-Wave recognizer independently satisfies its own causal morphology contract.
