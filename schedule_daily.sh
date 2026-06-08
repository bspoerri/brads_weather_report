#!/bin/bash
# Install (or refresh) a launchd agent that runs the coastal report
# every day at 5:00 AM local time and saves the PDF to reports/.
#
#   ./schedule_daily.sh           install / refresh the schedule
#   ./schedule_daily.sh remove    remove the schedule
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.brad.coastalreport"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ "${1:-}" == "remove" ]]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Removed schedule '$LABEL'."
    exit 0
fi

# Pick the interpreter that actually has the project's dependencies.
# launchd runs with a bare environment (no conda activation), so we must
# bake in an absolute path to a python that can import the deps -- NOT
# whatever `python3` happens to be on PATH when this script is run, which
# is often the dependency-less system python at /usr/bin/python3.
#
# Order of preference:
#   1. $COASTAL_PYTHON, if the caller set one explicitly
#   2. the project's conda env (weather_env)
#   3. python3 on PATH (manual / fallback)
pick_python() {
    local candidates=(
        "${COASTAL_PYTHON:-}"
        "$HOME/anaconda3/envs/weather_env/bin/python3"
        "$HOME/miniconda3/envs/weather_env/bin/python3"
        "$(command -v python3 || true)"
    )
    local c
    for c in "${candidates[@]}"; do
        [[ -n "$c" && -x "$c" ]] || continue
        if "$c" -c "import numpy" >/dev/null 2>&1; then
            echo "$c"
            return 0
        fi
    done
    return 1
}

if ! PYTHON="$(pick_python)"; then
    echo "ERROR: could not find a python3 with the project dependencies" >&2
    echo "       (tried \$COASTAL_PYTHON, the weather_env conda env, and PATH)." >&2
    echo "       Activate the env and re-run, or set COASTAL_PYTHON explicitly." >&2
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$DIR/logs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$DIR/run_daily.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>COASTAL_PYTHON</key>
        <string>$PYTHON</string>
        <key>PATH</key>
        <string>$(dirname "$PYTHON"):/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>$DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>5</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$DIR/logs/coastal_report.log</string>
    <key>StandardErrorPath</key>
    <string>$DIR/logs/coastal_report.err</string>
</dict>
</plist>
EOF

# Reload so re-running picks up changes.
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Scheduled '$LABEL' to run daily at 05:00 local time."
echo "  python : $PYTHON"
echo "  plist  : $PLIST"
echo "  logs   : $DIR/logs/"
echo "  PDFs   : $DIR/reports/"
echo
echo "Run once now to test:  ./run_daily.sh"
echo "Remove the schedule:   ./schedule_daily.sh remove"
