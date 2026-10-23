#!/usr/bin/env bash
# Installs the adaptive poller: a systemd user service, or an @reboot crontab entry if systemd is unavailable.
# With --with-server, also installs the widget server (systemd unit, or an @reboot cron line); without it, that is removed.
# Called by run.py: PYTHON=/path/to/python3 bash linux/install_task.sh [--with-server]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MARKER="# claude-usage-tracker"
UNIT_DIR="$HOME/.config/systemd/user"

err() { echo "ERROR: $*" >&2; exit 1; }

# Arguments are validated before anything is changed.
WITH_SERVER=0
for arg in "$@"; do
    case "$arg" in
        --with-server) WITH_SERVER=1 ;;
        *) err "unknown argument '$arg'. Usage: install_task.sh [--with-server]" ;;
    esac
done

# Interpreter: $PYTHON if set, otherwise python3 or python from PATH.
if [ -n "${PYTHON:-}" ]; then
    PY="$(command -v "$PYTHON" || true)"
else
    PY="$(command -v python3 || command -v python || true)"
fi
[ -n "$PY" ] || err "no usable Python interpreter found. Set PYTHON=/path/to/python3 or install Python 3."
echo "Interpreter: $PY"

# Escapes % and $ for systemd unit files.
esc() { local s="${1//%/%%}"; printf '%s' "${s//\$/\$\$}"; }
# Escapes % for crontab lines (cron treats % as a newline).
cron_esc() { local s="${1//%/\\%}"; printf '%s' "$s"; }

# Removes our systemd units (errors ignored).
remove_systemd_server() {
    systemctl --user disable --now claude-usage-server.service >/dev/null 2>&1 || true
    rm -f "$UNIT_DIR/claude-usage-server.service"
}
# The fixed-interval timer of older versions: the poller replaces it.
remove_systemd_timer() {
    systemctl --user disable --now claude-usage-tracker.timer >/dev/null 2>&1 || true
    rm -f "$UNIT_DIR/claude-usage-tracker.timer"
}

# Removes our crontab lines, only if there are any (errors ignored).
remove_cron_lines() {
    command -v crontab >/dev/null 2>&1 || return 0
    if crontab -l 2>/dev/null | grep -F "$MARKER" >/dev/null; then
        local tmp
        tmp="$(mktemp)"
        crontab -l 2>/dev/null | grep -vF "$MARKER" > "$tmp" || true
        crontab "$tmp"
        rm -f "$tmp"
    fi
}

if systemctl --user show-environment >/dev/null 2>&1; then
    echo "systemd (user) detected: installing units."
    mkdir -p "$UNIT_DIR"
    U_ROOT="$(esc "$ROOT")"
    U_PY="$(esc "$PY")"

    remove_systemd_timer
    if [ "$WITH_SERVER" -eq 0 ]; then
        remove_systemd_server
    fi

    # Long-running poller (it picks its own timing: 30 s to 10 min).
    cat > "$UNIT_DIR/claude-usage-tracker.service" <<EOF
[Unit]
Description=Claude usage readings (adaptive poller)

[Service]
Type=simple
WorkingDirectory=$U_ROOT
ExecStart="$U_PY" "$U_ROOT/poller.py"
Restart=on-failure
RestartSec=60

[Install]
WantedBy=default.target
EOF

    if [ "$WITH_SERVER" -eq 1 ]; then
        cat > "$UNIT_DIR/claude-usage-server.service" <<EOF
[Unit]
Description=Local server for the Claude usage widget

[Service]
Type=simple
WorkingDirectory=$U_ROOT
ExecStart="$U_PY" "$U_ROOT/server.py"
Restart=on-failure

[Install]
WantedBy=default.target
EOF
    fi

    systemctl --user daemon-reload
    systemctl --user enable claude-usage-tracker.service
    systemctl --user restart claude-usage-tracker.service
    if [ "$WITH_SERVER" -eq 1 ]; then
        systemctl --user enable --now claude-usage-server.service
    fi

    # Drop crontab lines left by an earlier cron-based install, so readings are not doubled.
    remove_cron_lines

    echo "Poller installed: systemd service claude-usage-tracker.service (started now)."
    if [ "$WITH_SERVER" -eq 1 ]; then
        echo "Server installed: claude-usage-server.service, starts with the user session."
    else
        echo "Widget server not installed (or removed)."
    fi
    echo "Verify: systemctl --user status claude-usage-tracker.service"
    echo "Keep it running without an open login session: loginctl enable-linger ${USER:-$(id -un)}"
else
    echo "systemd (user) unavailable: using crontab."
    command -v crontab >/dev/null 2>&1 || err "neither systemd (user) nor crontab is available."

    # Drop a systemd install from an earlier run, so readings are not doubled.
    if [ -d "$UNIT_DIR" ] && command -v systemctl >/dev/null 2>&1; then
        systemctl --user disable --now claude-usage-tracker.service >/dev/null 2>&1 || true
    fi
    remove_systemd_timer
    rm -f "$UNIT_DIR/claude-usage-tracker.service"
    remove_systemd_server

    # Keep crontab lines that are not ours, then add the new ones.
    TMP="$(mktemp)"
    (crontab -l 2>/dev/null || true) | grep -vF "$MARKER" > "$TMP" || true
    printf '@reboot cd "%s" && "%s" poller.py >/dev/null 2>&1 %s\n' \
        "$(cron_esc "$ROOT")" "$(cron_esc "$PY")" "$MARKER" >> "$TMP"
    if [ "$WITH_SERVER" -eq 1 ]; then
        printf '@reboot cd "%s" && "%s" server.py >/dev/null 2>&1 %s\n' \
            "$(cron_esc "$ROOT")" "$(cron_esc "$PY")" "$MARKER" >> "$TMP"
    fi
    crontab "$TMP"
    rm -f "$TMP"

    # @reboot only fires at the next boot: start the poller now (it exits at once if one already runs).
    nohup "$PY" "$ROOT/poller.py" >/dev/null 2>&1 &

    echo "Poller installed: starts at boot (@reboot crontab line), started now."
    if [ "$WITH_SERVER" -eq 1 ]; then
        echo "Server installed: starts at boot (@reboot crontab line)."
    else
        echo "Widget server not installed (or removed)."
    fi
    echo "Verify: crontab -l"
fi

echo "Log: $ROOT/data/tracker.log"
