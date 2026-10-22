#!/usr/bin/env bash
# Supprime la collecte automatique (unites systemd utilisateur et lignes crontab).
# Le dossier data/ est conserve.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MARQUEUR="# claude-usage-tracker"
UNIT_DIR="$HOME/.config/systemd/user"

# systemd : arret, suppression des fichiers d'unite (erreurs ignorees).
if systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user disable --now claude-usage-tracker.timer >/dev/null 2>&1 || true
    systemctl --user disable --now claude-usage-server.service >/dev/null 2>&1 || true
fi
rm -f "$UNIT_DIR/claude-usage-tracker.service" \
      "$UNIT_DIR/claude-usage-tracker.timer" \
      "$UNIT_DIR/claude-usage-server.service"
systemctl --user daemon-reload >/dev/null 2>&1 || true
echo "Unites systemd supprimees (si elles existaient)."

# crontab : on retire seulement nos lignes, uniquement si elles existent.
if command -v crontab >/dev/null 2>&1 && crontab -l 2>/dev/null | grep -F "$MARQUEUR" >/dev/null; then
    TMP="$(mktemp)"
    trap 'rm -f "$TMP"' EXIT
    crontab -l 2>/dev/null | grep -vF "$MARQUEUR" > "$TMP" || true
    crontab "$TMP"
    echo "Lignes crontab supprimees."
else
    echo "Aucune ligne crontab a supprimer."
fi

echo "Desinstallation terminee. Le dossier data/ est conserve : $ROOT/data"
