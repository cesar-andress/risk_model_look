# Threats-to-validity notes (established)

No speculative conclusions. Sources: protocol + audit reports already in repo.

1. **JIT-Defects4J line-label scope** — Line labels exist for test gold-positive commits; deleted lines are 0.0; primary localization compatibility historically emphasizes added lines.

2. **475 → 413 RQ1 complete-case selection** — 62 commits excluded due to mapping incompleteness between Policy-A ground truth and canonical Git line identities.

3. **Selection bias** — Excluded (incomplete) commits tend to have larger candidate universes / diffs; retained complete-case set is biased toward smaller diffs and higher buggy-line density among candidates (see complete-case bias report).

4. **2048 truncation** — Fully visible RQ1 commits: 413 → 304 at primary max length 2048 (CHANGED_ONLY). Partial candidate universes must not be scored silently as full RQ1.

5. **Git canonical vs JIT-Fine sets** — Model inputs use ordered Git reconstruction; upstream `added_code`/`removed_code` are lossy sets. Representation differs from original lossy JIT-Fine tokenizations.

6. **Llama access blocked** — M3 generalization currently blocked (`ACCESS_BLOCKED`); do not claim multi-family decoder generalization.

Results / effect sizes: not written (training / attribution results gates not started for scientific outputs).
