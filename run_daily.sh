#!/bin/bash
# Generate the coastal report and save the daily PDF.
# Invoked by the launchd agent (see schedule_daily.sh), but can also
# be run by hand.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
mkdir -p logs

# COASTAL_PYTHON is set by the launchd agent (schedule_daily.sh) to the
# interpreter that has the project's dependencies; fall back to PATH for
# manual runs.
PYTHON="${COASTAL_PYTHON:-$(command -v python3)}"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') running coastal report ==="
# --email sends the PDF to everyone on the distro list (recipients.txt).
exec "$PYTHON" main.py --email
