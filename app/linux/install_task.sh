#!/usr/bin/env bash
# Installs the periodic reading: a systemd user timer, or a crontab entry if systemd is unavailable.
# With --with-server, also installs the widget server (systemd unit, or an @reboot cron line); without it, that is removed.
# Called by run.py: PYTHON=/path/to/python3 bash linux/install_task.sh N [--with-server]
# Usage: install_task.sh [MINUTES] [--with-server]   (MINUTES defaults to 10, range 1-1439)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MARKER="# claude-usage-tracker"
UNIT_DIR="$HOME/.config/systemd/user"

err() { echo "ERROR: $*" >&2; exit 1; }

# Arguments are validated before anything is changed.
MINUTES=10
WITH_SERVER=0
MINUTES_GIVEN=0
for arg in "$@"; do
    case "$arg" in
        --with-server) WITH_SERVER=1 ;;
        -*) err "unknown option '$arg'. Usage: install_task.sh [MINUTES] [--with-server]" ;;
        *)
            [ "$MINUTES_GIVEN" -eq 0 ] || err "MINUTES was given more than once."
            MINUTES="$arg"
            MINUTES_GIVEN=1
            ;;
    esac
done
case "$MINUTES" in
    ''|*[!0-9]*) err "MINUTES must be a positive integer between 1 and 1439 (got '$MINUTES')." ;;
esac
[ "${#MINUTES}" -le 4 ] || err "MINUTES must be between 1 and 1439 (got '$MINUTES')."
MINUTES=$((10#$MINUTES))
if [ "$MINUTES" -lt 1 ] || [ "$MINUTES" -gt 1439 ]; then
    err "MINUTES must be between 1 and 1439 (got '$MINUTES')."
fi

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

    if [ "$WITH_SERVER" -eq 0 ]; then
        remove_systemd_server
    fi

    # One-shot reading service, triggered by the timer.
    cat > "$UNIT_DIR/claude-usage-tracker.service" <<EOF
[Unit]
Description=Claude usage reading

[Service]
Type=oneshot
WorkingDirectory=$U_ROOT
ExecStart="$U_PY" "$U_ROOT/claude_usage.py"
EOF

    # Timer: first reading 1 minute after boot, then every MINUTES minutes.
    cat > "$UNIT_DIR/claude-usage-tracker.timer" <<EOF
[Unit]
Description=Periodic timer for the Claude usage reading

[Timer]
OnBootSec=1min
OnUnitActiveSec=${MINUTES}min
Persistent=true

[Install]
WantedBy=timers.target
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
    systemctl --user enable --now claude-usage-tracker.timer
    if [ "$WITH_SERVER" -eq 1 ]; then
        systemctl --user enable --now claude-usage-server.service
    fi

    # Drop crontab lines left by an earlier cron-based install, so readings are not doubled.
    remove_cron_lines

    echo "Task installed: one reading every $MINUTES minutes (systemd timer claude-usage-tracker.timer)."
    if [ "$WITH_SERVER" -eq 1 ]; then
        echo "Server installed: claude-usage-server.service, starts with the user session."
    else
        echo "Widget server not installed (or removed)."
    fi
    echo "Verify: systemctl --user list-timers claude-usage-tracker.timer"
    echo "Keep it running without an open login session: loginctl enable-linger ${USER:-$(id -un)}"
else
    echo "systemd (user) unavailable: using crontab."
    command -v crontab >/dev/null 2>&1 || err "neither systemd (user) nor crontab is available."
    [ "$MINUTES" -le 59 ] || err "without systemd, MINUTES must be between 1 and 59 (crontab limit)."

    # Drop a systemd install from an earlier run, so readings are not doubled.
    if [ -d "$UNIT_DIR" ] && command -v systemctl >/dev/null 2>&1; then
        systemctl --user disable --now claude-usage-tracker.timer >/dev/null 2>&1 || true
    fi
    rm -f "$UNIT_DIR/claude-usage-tracker.timer" "$UNIT_DIR/claude-usage-tracker.service"
    remove_systemd_server

    # Keep crontab lines that are not ours, then add the new ones.
    TMP="$(mktemp)"
    (crontab -l 2>/dev/null || true) | grep -vF "$MARKER" > "$TMP" || true
    printf '*/%s * * * * cd "%s" && "%s" claude_usage.py >/dev/null 2>&1 %s\n' \
        "$MINUTES" "$(cron_esc "$ROOT")" "$(cron_esc "$PY")" "$MARKER" >> "$TMP"
    if [ "$WITH_SERVER" -eq 1 ]; then
        printf '@reboot cd "%s" && "%s" server.py >/dev/null 2>&1 %s\n' \
            "$(cron_esc "$ROOT")" "$(cron_esc "$PY")" "$MARKER" >> "$TMP"
    fi
    crontab "$TMP"
    rm -f "$TMP"

    echo "Task installed: one reading every $MINUTES minutes (crontab)."
    if [ "$WITH_SERVER" -eq 1 ]; then
        echo "Server installed: starts at boot (@reboot crontab line)."
    else
        echo "Widget server not installed (or removed)."
    fi
    echo "Verify: crontab -l"
fi

echo "Log: $ROOT/data/tracker.log"
