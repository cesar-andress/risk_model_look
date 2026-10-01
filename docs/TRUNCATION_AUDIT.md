# TRUNCATION_AUDIT.md

**Policy:** `WHOLE_SEGMENT_PREFIX_TRUNCATION_V1`  
Never leaves a partially included semantic code payload line.

Primary representation: **CHANGED_ONLY**.  
Lengths: primary **2048**, ablation **4096**.  
CTX3 is a predeclared representation ablation (not primary).

---

## CHANGED_ONLY — all splits

| Split | Max len | Truncated | % |
|-------|--------:|----------:|--:|
| train | 2048 | 3033 / 16374 | 18.52 |
| valid | 2048 | 899 / 5465 | 16.45 |
| test | 2048 | 1088 / 5480 | 19.85 |
| train | 4096 | 1570 / 16374 | 9.59 |
| valid | 4096 | 440 / 5465 | 8.05 |
| test | 4096 | 586 / 5480 | 10.69 |

## CHANGED_ONLY — primary RQ1 (N=413)

| Max len | Truncated commits | % | RQ1_VISIBLE_N | cand lost | pos lost | neg lost |
|--------:|------------------:|--:|--------------:|----------:|---------:|---------:|
| 2048 | 169 | 40.92 | **304** | 6341 | 550 | (rest) |
| 4096 | 112 | 27.12 | **345** | 3959 | 288 | (rest) |

`RQ1_VISIBLE_N` = complete-case commits with **zero** RQ1 candidate lines dropped by truncation.  
Truncated RQ1 lines are marked conceptually as `RQ1_LINE_TRUNCATED` for evaluation scoping — **not** relabelled negative.

## CTX3 ablation

| Scope | Max len | Truncated | % | RQ1_VISIBLE_N |
|-------|--------:|----------:|--:|--------------:|
| all 27319 | 2048 | 8723 | 31.93 | 244 |
| rq1_primary 413 | 2048 | 230 | 55.69 | 244 |
| all 27319 | 4096 | 4998 | 18.29 | 312 |
| rq1_primary 413 | 4096 | 156 | 37.77 | 312 |

Primary choices (CHANGED_ONLY, 2048) were frozen **before** inspecting these numbers. Test truncation is descriptive only.
