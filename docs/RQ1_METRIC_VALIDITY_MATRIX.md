# RQ1_METRIC_VALIDITY_MATRIX.md

Cell legend:

- **VALID** — mathematically applicable under the stated universe  
- **VALID_WITH_SCOPE_CAVEAT** — applicable only with explicit scope language  
- **INVALID_UNKNOWN_NEGATIVES** — requires known negatives; unknowns present  
- **NOT_APPLICABLE** — metric not defined for that setup  

| Universe / Policy | Top-5 | Top-10 | IFA | Recall@20%Effort | Effort@20%Recall | MRR | Hunk coverage |
|-------------------|-------|--------|-----|------------------|------------------|-----|---------------|
| JIT-Fine evaluator \(U_{\mathrm{JITFINE}}\) / Policy A (N=475) | VALID | VALID | VALID | VALID | VALID | VALID_WITH_SCOPE_CAVEAT | NOT_APPLICABLE |
| JIT-Block eval (same Layer-B pickle; DP cohort filtered) | VALID | VALID | VALID | VALID | VALID | VALID_WITH_SCOPE_CAVEAT | NOT_APPLICABLE |
| Full canonical Git / Policy B | INVALID_UNKNOWN_NEGATIVES | INVALID_UNKNOWN_NEGATIVES | INVALID_UNKNOWN_NEGATIVES | INVALID_UNKNOWN_NEGATIVES | INVALID_UNKNOWN_NEGATIVES | INVALID_UNKNOWN_NEGATIVES | VALID_WITH_SCOPE_CAVEAT |
| Complete-label Git subset / Policy C (N=58) | VALID | VALID | VALID | VALID | VALID | VALID | VALID_WITH_SCOPE_CAVEAT |
| Positive-complete subset / Policy D (N=352) | VALID_WITH_SCOPE_CAVEAT | VALID_WITH_SCOPE_CAVEAT | INVALID_UNKNOWN_NEGATIVES | INVALID_UNKNOWN_NEGATIVES | INVALID_UNKNOWN_NEGATIVES | VALID_WITH_SCOPE_CAVEAT | NOT_APPLICABLE |

### Notes

1. **Top-k** under Policy D is only valid if the ranking domain is fully specified (e.g. Layer-B rows of those commits), not silently “all Git added lines”.  
2. **IFA / effort** refuse UNKNOWN via `src/metrics/label_universe_guard.py`.  
3. **Hunk coverage** needs file/hunk IDs from Git reconstruction; independent of Layer-B binary labels.
