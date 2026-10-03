#!/usr/bin/env bash
# Resume-safe TEST attribution driver. Offline. No encoder. No paper edits.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
LOG="$ROOT/artifacts/test_attribution/logs/gpu_chain.log"
mkdir -p "$ROOT/artifacts/test_attribution/logs"
exec >>"$LOG" 2>&1
echo "===== $(date -Is) start chain ====="
for b in CHEAP G I J K; do
  echo "===== $(date -Is) block $b ====="
  .venv/bin/python -u scripts/run_test_attribution.py --block "$b"
done
.venv/bin/python -u scripts/summarize_test_attribution.py
echo "===== $(date -Is) chain complete ====="
