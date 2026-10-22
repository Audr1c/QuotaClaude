#!/usr/bin/env bash
# Installe la collecte periodique : timer systemd (utilisateur), sinon crontab.
# Usage : installer_tache.sh [MINUTES] [--avec-serveur]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
    echo "Erreur : python3 (ou python) introuvable. Installez Python 3." >&2
    exit 1
fi

# Arguments : MINUTES (defaut 10) et option --avec-serveur.
MINUTES=10
AVEC_SERVEUR=0
for arg in "$@"; do
    case "$arg" in
        --avec-serveur) AVEC_SERVEUR=1 ;;
        -*) echo "Erreur : option inconnue '$arg'." >&2; exit 1 ;;
        *) MINUTES="$arg" ;;
    esac
done
case "$MINUTES" in
    ''|*[!0-9]*) echo "Erreur : MINUTES doit etre un entier positif." >&2; exit 1 ;;
esac
if [ "$MINUTES" -lt 1 ]; then
    echo "Erreur : MINUTES doit etre un entier positif." >&2
    exit 1
fi

MARQUEUR="# claude-usage-tracker"
UNIT_DIR="$HOME/.config/systemd/user"

# Echappe % et $ pour les fichiers d'unite systemd.
esc() { local s="${1//%/%%}"; printf '%s' "${s//\$/\$\$}"; }

if systemctl --user show-environment >/dev/null 2>&1; then
    echo "systemd (utilisateur) detecte : installation des unites."
    mkdir -p "$UNIT_DIR"
    U_ROOT="$(esc "$ROOT")"
    U_PY="$(esc "$PY")"

    # Service de collecte (one-shot), declenche par le timer.
    cat > "$UNIT_DIR/claude-usage-tracker.service" <<EOF
[Unit]
Description=Releve de l'usage Claude

[Service]
Type=oneshot
WorkingDirectory=$U_ROOT
ExecStart="$U_PY" "$U_ROOT/claude_usage.py"
EOF

    # Timer : premiere collecte 1 min apres le demarrage, puis toutes les MINUTES.
    cat > "$UNIT_DIR/claude-usage-tracker.timer" <<EOF
[Unit]
Description=Timer du releve periodique de l'usage Claude

[Timer]
OnBootSec=1min
OnUnitActiveSec=${MINUTES}min
Persistent=true

[Install]
WantedBy=timers.target
EOF

    if [ "$AVEC_SERVEUR" -eq 1 ]; then
        cat > "$UNIT_DIR/claude-usage-server.service" <<EOF
[Unit]
Description=Serveur local du widget Claude usage

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
    if [ "$AVEC_SERVEUR" -eq 1 ]; then
        systemctl --user enable --now claude-usage-server.service
    fi

    echo "Installe : collecte toutes les $MINUTES min (timer claude-usage-tracker)."
    if [ "$AVEC_SERVEUR" -eq 1 ]; then
        echo "Installe : serveur du widget (claude-usage-server), http://127.0.0.1:8765/"
    fi
    echo "Verifier : systemctl --user list-timers"
    echo "Pour que cela tourne sans session ouverte : loginctl enable-linger $USER"
else
    echo "systemd (utilisateur) indisponible : utilisation de crontab."
    if ! command -v crontab >/dev/null 2>&1; then
        echo "Erreur : ni systemd (utilisateur) ni crontab disponibles." >&2
        exit 1
    fi
    if [ "$MINUTES" -gt 59 ]; then
        echo "Erreur : avec crontab, MINUTES doit etre entre 1 et 59." >&2
        exit 1
    fi

    # Retire les anciennes lignes du projet, puis ajoute les nouvelles.
    TMP="$(mktemp)"
    trap 'rm -f "$TMP"' EXIT
    (crontab -l 2>/dev/null || true) | grep -vF "$MARQUEUR" > "$TMP" || true
    echo "*/$MINUTES * * * * cd \"$ROOT\" && \"$PY\" claude_usage.py >/dev/null 2>&1 $MARQUEUR" >> "$TMP"
    if [ "$AVEC_SERVEUR" -eq 1 ]; then
        echo "@reboot cd \"$ROOT\" && \"$PY\" server.py >/dev/null 2>&1 $MARQUEUR" >> "$TMP"
    fi
    crontab "$TMP"

    echo "Installe : collecte toutes les $MINUTES min (crontab)."
    if [ "$AVEC_SERVEUR" -eq 1 ]; then
        echo "Installe : serveur du widget au demarrage (@reboot), http://127.0.0.1:8765/"
    fi
    echo "Verifier : crontab -l"
fi

echo "Journal de la collecte : $ROOT/data/tracker.log"
