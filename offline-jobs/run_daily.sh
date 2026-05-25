#!/usr/bin/env bash
# Daily entrypoint invoked by cron.
#
# Runs the collector first, then the cleanup. `set -e` ensures cleanup is
# skipped if the collector fails, and the non-zero exit propagates to cron.
#
# Install (run once):
#   crontab -e
#   # Append (Mon–Fri at 18:30 local):
#   30 18 * * 1-5 /home/mfong415/projects/equity-analysis-tools/equity-rotation-tracking/offline-jobs/run_daily.sh
#
# Inspect:
#   tail -f offline-jobs/logs/run_daily.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs

# Activate the shared venv created by `python -m venv .venv`.
if [[ -f .venv/bin/activate ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
else
    echo "ERROR: .venv not found. Run: python -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

# Make `python -m data_collector_job` find the package in this directory.
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*" | tee -a logs/run_daily.log; }

log "=== daily run start ==="

log "collector: starting"
python -m data_collector_job >> logs/collector.log 2>&1
log "collector: ok"

log "cleanup: starting"
python -m data_cleanup_job >> logs/cleanup.log 2>&1
log "cleanup: ok"

log "=== daily run done ==="
