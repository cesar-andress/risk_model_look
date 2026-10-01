# Model Input Leakage Audit — M1 Pilot

**Gate:** PILOT_TRAINING_GATE  
**Date:** 2026-10-01  
**Verdict:** PASS (see runtime summary)

## Scope

Prove that model-visible rendered prompt text excludes internal metadata fields
that may exist in JSONL records. Natural source-code occurrences of words such
as `bug`, `fix`, `label`, `0`, or `1` are **not** treated as metadata leakage.

## Forbidden markers (must not appear in structured render)

- `commit_label`
- `is_buggy_commit`
- `rq1_status`
- `RQ1_POSITIVE`
- `RQ1_NEGATIVE`
- `NOT_IN_RQ1_UNIVERSE`
- `rq1_primary_commit`
- `stable_line_id`
- `ground_truth`

Internal dataset IDs and target labels must not be injected into the chat prompt
as metadata. The supervised target (`0`/`1`) is appended only as the training
label token after the generation prompt, never as free-text metadata inside the
user/system content.

## Method

1. Structured text is produced solely by `render_record` →
   `CHANGED_ONLY` structured diff (`STRUCTURED_FORMAT_VERSION` / context=0).
2. Chat wrap uses frozen `PROMPT_TEMPLATE_VERSION=1` via `wrap_chat_plaintext`
   (system classifier instruction + user structured diff).
3. `audit_structured_leakage(structured_text)` scans for forbidden markers.
4. Pilot runner checks a deterministic sample of **500** TRAIN records before
   optimization. Any hit → immediate STOP / gate FAIL.

## Results

Runtime (`artifacts/pilot_training/m1_pilot_summary.json` → `leakage_audit`):

- `n_checked`: 500
- `n_leaked`: 0
- `verdict`: **PASS**

Gate stopped immediately on any hit; none observed.

## Notes

- Span metadata (`stable_line_id`, `rq1_status`) exists in the **span registry**
  for token↔line mapping, not in the rendered character stream consumed by the
  model.
- This audit does not claim that source code never contains the substrings above
  as natural identifiers; the check is for our **metadata field names / status
  enums** being injected by the renderer.
