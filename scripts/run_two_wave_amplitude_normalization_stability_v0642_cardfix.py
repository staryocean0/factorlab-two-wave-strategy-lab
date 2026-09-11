#!/usr/bin/env python3
"""Output-layer fix for the frozen v0.6.42 attribution runner."""
from __future__ import annotations

import scripts.run_two_wave_amplitude_normalization_stability_v0642 as runner


def write_card(path, result):
    rank = result["threshold_free_rank_comparisons"]
    cats = result["harm_counterfactual_attribution"]
    harm = result["one_sided_summary_by_semantic"]["introduced_harm"]
    stable = result["stable_both_rescue_summary"]
    topology = result["controls"]["v0637_pair_change_topology"]
    lines = [
        "# Two-Wave v0.6.42 amplitude-normalization stability attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        f"Diagnostic universe: **{result['diagnostic_pairs']}** = {topology['both']} stable both-rescue + {result['one_sided_rows']} one-sided; harm counterfactual rows = {cats['count']}.",
        "",
        "| quantity | stable median | harm median | rank P(harm > stable) |",
        "|---|---:|---:|---:|",
        f"| amplitude-unit SRD | {stable['amplitude_unit_SRD']['median']:.6f} | {harm['amplitude_unit_SRD']['median']:.6f} | {rank['harm_amplitude_unit_SRD_gt_stable']:.6f} |",
        f"| max raw-W1 SRD | {stable['max_raw_w1_SRD']['median']:.6f} | {harm['max_raw_w1_SRD']['median']:.6f} | {rank['harm_max_raw_w1_SRD_gt_stable']:.6f} |",
        f"| max normalized-W1 SRD | {stable['max_normalized_w1_SRD']['median']:.6f} | {harm['max_normalized_w1_SRD']['median']:.6f} | {rank['harm_max_normalized_w1_SRD_gt_stable']:.6f} |",
        f"| cycle-amplitude-imbalance SRD | {stable['cycle_amplitude_imbalance_SRD']['median']:.6f} | {harm['cycle_amplitude_imbalance_SRD']['median']:.6f} | {rank['harm_cycle_amplitude_imbalance_SRD_gt_stable']:.6f} |",
        "",
        f"Harm counterfactual attribution counts: `{cats['counts']}`.",
        f"Harm signed amplitude-unit change fractions: `{result['harm_signed_change_fractions']['amplitude_unit']}`.",
        f"Harm signed raw-W1 change fractions: `{result['harm_signed_change_fractions']['max_raw_w1']}`.",
        f"Harm signed normalized-W1 change fractions: `{result['harm_signed_change_fractions']['max_normalized_w1']}`.",
        "",
        "v0.6.42 is diagnostic only. It does not change the recognizer, tune the inherited 0.15 ceiling, or authorize a gate.",
    ]
    path.write_text("\n".join(lines) + "\n")


runner.write_card = write_card
runner.main()
