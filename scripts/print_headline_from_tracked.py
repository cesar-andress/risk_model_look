#!/usr/bin/env python3
"""Print headline frozen tables from TRACKED JSON only (no raw jobs, no GPU)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rq1 = ROOT / "artifacts/test_attribution/summaries/rq1_summary.csv"
    freeze = json.loads((ROOT / "artifacts/emse_final/EMSE_FINAL_RESULTS_FREEZE.json").read_text())
    diag = json.loads((ROOT / "artifacts/emse_final/emse_final_diagnostics.json").read_text())
    stab = json.loads(
        (ROOT / "artifacts/test_attribution/metrics/stability/seed_stability.json").read_text()
    )
    rq2 = json.loads((ROOT / "artifacts/test_attribution/statistics/rq2_stats.json").read_text())
    cpu = json.loads((ROOT / "artifacts/tosem_extension/cpu_reanalysis.json").read_text())
    excl = json.loads(
        (ROOT / "artifacts/test_attribution/summaries/rq2_excluded_3.json").read_text()
    )
    sec = json.loads(
        (ROOT / "artifacts/test_attribution/summaries/rq1_secondary_metrics.json").read_text()
    )

    print("FREEZE", freeze.get("freeze_sha256"))
    print("NUMERICAL_GATE", freeze.get("NUMERICAL_GATE"))
    print("--- RQ1 summary.csv ---")
    print(rq1.read_text())
    print("--- RQ1 baselines (cpu_reanalysis) ---")
    b = cpu["rq1_baselines"]
    print("N", b["N"], "length", b["B_LENGTH_mean_recall20"], "random", b["B_RANDOM_mean_recall20"])
    print("--- RQ1 secondary (frozen job fields) ---")
    print(json.dumps(sec["methods"], indent=2))
    print("--- RQ2 Att vs GxI ---")
    c0 = rq2["contrasts"][0]
    print("n_included", c0["n_included"], "n_excluded", c0["n_excluded"], "delta", c0["bootstrap"]["point"])
    print("excluded commits", excl["commit_ids"], excl["reason"])
    print("--- TEST all-line seed_stability (pair means) ---")
    for m in ("attention", "grad_x_input", "occlusion"):
        d = stab["pairs_by_method"][m]
        print(m, {k: round(v["mean_rho"], 3) for k, v in d.items()})
    print("--- EMSE RQ1>=5 seed_stability (mean_across_commits) ---")
    ss = diag.get("seed_stability") or {}
    for m, row in ss.items():
        if isinstance(row, dict) and isinstance(row.get("raw"), dict):
            print(m, "raw", round(row["raw"]["mean_across_commits"], 3), "n", row["raw"].get("n_commits"))
        else:
            print(m, row)


if __name__ == "__main__":
    main()
