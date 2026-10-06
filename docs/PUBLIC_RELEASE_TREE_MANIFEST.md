# PUBLIC_RELEASE_TREE_MANIFEST.md

Date: 2026-10-06  
Task: SUPERPROMPT 34 release-candidate hygiene  
Purpose: document which `docs/` materials remain in the tagged public tree.

A GitHub-linked Zenodo archive preserves the **entire tagged Git tree**.
This manifest records intentional curation before `v1.0.0`.

Git history of removed paths remains available; files are not erased from history.

## Retained public docs (purpose)

| Path / group | Purpose |
|--------------|---------|
| `AMENDMENT_AND_PROVENANCE_LOG.md` | Amendments, identifier semantics, planned-analysis accounting |
| `EMSE_FINAL_ANALYSIS_LOCK.md`, `EMSE_FINAL_CLAIM_LEDGER.md` | Analysis lock + claim ledger |
| `ATTRIBUTION_PROTOCOL_V1*.md`, `STATISTICAL_ANALYSIS_PROTOCOL_V1*.md` | Frozen protocols |
| `ATTRIBUTION_METHOD_CONTRACT.md`, `ATTRIBUTION_COMPUTE_PLAN.md`, `RQ_METRIC_CONTRACT.md`, `RQ1_*`, `LINE_*`, `DIFF_*`, `CANONICAL_DIFF_CONTRACT.md`, `TOKEN_LINE_MAPPING_REPORT.md` | Method/metric/data contracts for reproduction |
| `DATA_PROVENANCE.md`, `DATASET_*`, `DATA_ACQUISITION_PLAN.md`, `GROUND_TRUTH_*`, `POLICY_A_*`, `PROCESSED_DATASET_CONTRACT.md`, `LINE_LABEL_*` | Dataset provenance and mapping |
| `FLOAT32_PATH_PROVENANCE.md`, `SEED_STABILITY_RECONCILIATION.md`, `LENGTH_STABILITY_DENOMINATOR_AUDIT.md`, `CONTEXT4096_DENOMINATOR_AUDIT.md` | Diagnostic interpretation |
| `ENCODER_BASELINE_RESOLUTION.md`, `OPERATOR_SENSITIVITY_RESOLUTION.md` | Pre-specified but unexecuted items |
| `TOSEM_EXTENSION_PROTOCOL_LOCK.md`, `TOSEM_EXTENSION_PROTOCOL_AUDIT.md` | Extension freeze protocol (historical filename) |
| `VALIDATION_ATTRIBUTION_REHEARSAL_PROTOCOL.md`, `TRUNCATION_AUDIT.md`, `MODEL_INPUT_LEAKAGE_AUDIT.md` | Execution/validity audits |
| `M1_*_TRAINING_REPORT.md`, `ENVIRONMENT_REPORT.md` | Training/environment provenance |
| `NOVELTY_GATE.md`, `NOVELTY_COLLISION_MATRIX.md`, `STATE_OF_ART_NOVELTY_MAP.md`, literature CSVs, `REFERENCE_LEDGER.md` | Novelty/bib audit trail |
| `DECISION_LOG.md`, `RESIDUAL_TRANSFORMS_LEDGER.md` | Decision/transform provenance |
| `PUBLIC_ARTIFACT_AUDIT.md`, `FRESH_CLONE_REPRODUCTION_REPORT.md`, `ZENODO_RELEASE_PLAN.md`, this manifest | Release audit trail |
| `PICKLE_SECURITY_AUDIT.md`, `LARGE_FILE_AUDIT.md`, `JITBLOCK_REPLICATION_AUDIT.md` | Security/size/replication checks |
| `schemas/` | JSON schemas used by tooling |

Root retained: `README.md`, `REPRODUCIBILITY.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `CITATION.cff`, `.zenodo.json`, `environment.yml`.

## Removed before v1.0.0 (why)

| Path | Why removed |
|------|-------------|
| `STATUS.md` | Stale project dashboard (wrong title; attribution marked NOT_STARTED) |
| `REPRODUCE.md` | Contradicted `REPRODUCIBILITY.md` (“science not available yet”) |
| `docs/FINAL_VENUE_DECISION.md` | Venue-decision process note |
| `docs/ADVERSARIAL_REVIEW_RESPONSE.md` | Reviewer-attack / process brainstorming |
| `docs/REVIEWER_ATTACK_AUDIT.md` | Internal attack checklist |
| `docs/MERGE_PLAN.md`, `docs/PAPER_INTEGRATION_PLAN.md` | Internal engineering plans |
| `docs/GITHUB_RELEASE_PLAN.md` | Superseded by `ZENODO_RELEASE_PLAN.md` |
| `docs/ATTRIBUTION_ENGINE_DESIGN.md` | AI/design process note |
| `docs/EXPERIMENT_PROTOCOL_V0.md` | Superseded protocol |
| `docs/REPOSITORY_AUDIT_REPORT.md`, `docs/REPOSITORY_FINAL_STATE.md`, `docs/GITIGNORE_AUDIT.md`, `docs/PROJECT_REPOSITORY_MAP.csv` | Internal repo management |
| `docs/EMSE_SUBMISSION_REQUIREMENTS.md` | Journal process notes |
| `docs/TOSEM_EXTENSION_CLAIM_LEDGER.md` | Rejected-venue claim ledger (protocol lock retained) |
| `docs/paper_notes/*` | Internal manuscript scaffolds |
| `docs/reviews/CLAUDE_DESIGN_REVIEW_2026-10-01.md` | AI design-review process note |

## Counts

- Docs entries before hygiene (directory listing): **78**
- Docs entries after hygiene: **62**
- Tracked paths removed in this candidate: **20** (including root `STATUS.md` / `REPRODUCE.md`)
