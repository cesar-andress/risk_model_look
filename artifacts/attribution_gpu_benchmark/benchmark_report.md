# Attribution GPU engineering benchmark

**ENGINEERING BENCHMARK ONLY — NOT_SCIENTIFIC_RESULT — NOT validation rehearsal — NOT test attribution — NOT RQ results**

Written: 2026-10-03T08:19:32+02:00

This is an ENGINEERING BENCHMARK, not a SCIENTIFIC ATTRIBUTION REHEARSAL.

Adapter verified: `a764d2f57e6586cf61b9c38d7dea4bd1b5a2da73fd4b14e5a3f4ee5eb91b02bf` seed=13 epoch=2

Validation rehearsal readiness (engineering): READY

Do not start N=64 from this file.

Primary measurements (seed 13 / epoch 2, RTX 4090, NF4, max_len cap 2048):

- Attention ~2.8–7.4 maps/s depending on token length (peak ~15 GiB at 2036 tokens)
- Grad×Input ~1.3–3.7 backwards/s
- IG 50-step engineering runtime 4.32 s on a 219-token prompt (~11.6 steps/s)
- Occlusion SEGMENT_DELETE ~13–17 regions/s; selected batch 4 (seq vs batch max abs diff 0)
- IG chunk 1 vs 4 max abs diff 0.013 (NF4); selected engineering chunk = 1 for scientific runs
