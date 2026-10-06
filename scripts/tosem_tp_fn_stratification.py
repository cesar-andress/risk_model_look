#!/usr/bin/env python3
"""POST-HOC ROBUSTNESS: TP/FN stratification from frozen M1 TEST predictions."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from src.experiments.missingness_validity import attribution_job_is_valid, faith_aopc_is_valid

OUT = ROOT / "artifacts" / "tosem_extension"
ATTR = ROOT / "artifacts" / "test_attribution"
PRED = ROOT / "data" / "results" / "m1_final"
SEEDS = (13, 42, 73)


def loadj(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> int:
    cohorts = loadj(ATTR / "cohorts" / "COHORT_INTEGRITY.json")
    rq1 = set(cohorts["rq1_primary_304"]["commit_ids"])
    pos = cohorts["positive_475"]["commit_ids"]

    pred = defaultdict(dict)  # cid -> seed -> predicted_label
    for seed in SEEDS:
        path = PRED / f"seed_{seed}" / "test_predictions.csv"
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pred[row["commit_id"]][seed] = int(row["predicted_label"])

    recall = defaultdict(lambda: defaultdict(dict))
    aopc = defaultdict(lambda: defaultdict(dict))
    for seed in SEEDS:
        for method in ("attention", "grad_x_input", "occlusion"):
            for cid in pos:
                u = loadj(ATTR / "raw" / "positive_475" / f"seed_{seed}" / method / f"ml2048_{cid}.json")
                if u and attribution_job_is_valid(u, method):
                    rec20 = (u.get("rq1") or {}).get("recall_at_20pct_effort")
                    if rec20 is not None:
                        recall[method][cid][seed] = float(rec20)
                f = loadj(
                    ATTR / "raw" / "positive_475" / "faithfulness" / f"seed_{seed}" / method / f"{cid}.json"
                )
                if faith_aopc_is_valid(f, method, u):
                    aopc[method][cid][seed] = float(f["aopc"])

    def collapse_metric(by_cid_seed, cids):
        out = {}
        for cid in cids:
            xs = [by_cid_seed.get(cid, {}).get(s) for s in SEEDS]
            xs = [x for x in xs if x is not None]
            if len(xs) >= 2:
                out[cid] = float(sum(xs) / len(xs))
        return out

    def collapse_pred(cids):
        """Commit is TP if majority of seeds with predictions is 1; require >=2 seeds."""
        labels = {}
        for cid in cids:
            xs = [pred.get(cid, {}).get(s) for s in SEEDS]
            xs = [x for x in xs if x is not None]
            if len(xs) >= 2:
                labels[cid] = 1 if sum(xs) >= (len(xs) / 2.0) else 0
        return labels

    labels_rq1 = collapse_pred(rq1)
    labels_pos = collapse_pred(pos)

    blob = {
        "role": "POST-HOC ROBUSTNESS",
        "protocol_secondary": "prediction_correctness_association POINT_BISERIAL SECONDARY_ESTIMATION",
        "note": "Gold-positive TEST commits only. TP = predicted_label 1 at frozen seed threshold; FN = 0. Majority across >=2 seeds. Does not alter primary cohorts.",
        "created": datetime.now(timezone.utc).isoformat(),
        "by_method": {},
    }

    for method in ("attention", "grad_x_input", "occlusion"):
        rec_m = collapse_metric(recall[method], rq1)
        aopc_m = collapse_metric(aopc[method], pos)
        method_out = {"rq1_recall20": {}, "rq2_aopc": {}}
        for name, metric_map, labs in (
            ("rq1_recall20", rec_m, labels_rq1),
            ("rq2_aopc", aopc_m, labels_pos),
        ):
            tp = [metric_map[c] for c in metric_map if labs.get(c) == 1]
            fn = [metric_map[c] for c in metric_map if labs.get(c) == 0]
            both = [(metric_map[c], labs[c]) for c in metric_map if c in labs]
            y = np.array([v for v, _ in both], dtype=float)
            x = np.array([lab for _, lab in both], dtype=float)
            pbr = None
            if y.size >= 3 and x.std() > 0 and y.std() > 0:
                pbr = float(np.corrcoef(x, y)[0, 1])
            method_out[name] = {
                "n_tp": len(tp),
                "n_fn": len(fn),
                "mean_tp": float(np.mean(tp)) if tp else None,
                "mean_fn": float(np.mean(fn)) if fn else None,
                "median_tp": float(np.median(tp)) if tp else None,
                "median_fn": float(np.median(fn)) if fn else None,
                "point_biserial": pbr,
            }
        blob["by_method"][method] = method_out

    (OUT / "tp_fn_stratification.json").write_text(json.dumps(blob, indent=2, sort_keys=True) + "\n")
    print(json.dumps({m: blob["by_method"][m] for m in blob["by_method"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
