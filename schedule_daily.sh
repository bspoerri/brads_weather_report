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

PYTHON="$(command -v python3)"
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
