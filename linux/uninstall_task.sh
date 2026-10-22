#!/usr/bin/env bash
# Removes the periodic reading: systemd user units and crontab lines marked "# claude-usage-tracker".
# Called by run.py: bash linux/uninstall_task.sh. The data/ folder is kept.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MARKER="# claude-usage-tracker"
UNIT_DIR="$HOME/.config/systemd/user"

# systemd: stop and disable, then delete the unit files (errors ignored).
if systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user disable --now claude-usage-tracker.timer >/dev/null 2>&1 || true
    systemctl --user disable --now claude-usage-server.service >/dev/null 2>&1 || true
fi
rm -f "$UNIT_DIR/claude-usage-tracker.service" \
      "$UNIT_DIR/claude-usage-tracker.timer" \
      "$UNIT_DIR/claude-usage-server.service"
systemctl --user daemon-reload >/dev/null 2>&1 || true
echo "Systemd units removed (if they existed)."

# crontab: remove only our lines, and only if there are any.
if command -v crontab >/dev/null 2>&1 && crontab -l 2>/dev/null | grep -F "$MARKER" >/dev/null; then
    TMP="$(mktemp)"
    crontab -l 2>/dev/null | grep -vF "$MARKER" > "$TMP" || true
    crontab "$TMP"
    rm -f "$TMP"
    echo "Crontab lines removed."
else
    echo "No crontab lines to remove."
fi

echo "Uninstall complete. The data/ folder is kept: $ROOT/data"
