#!/usr/bin/env bash
# Releve immediat : collecte, tests, puis demarrage du serveur du widget.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
    echo "Erreur : python3 (ou python) introuvable. Installez Python 3." >&2
    exit 1
fi

# Collecte : on garde le code de retour sans arreter le script.
echo "== Releve de l'usage Claude =="
STATUS=0
"$PY" claude_usage.py || STATUS=$?
if [ "$STATUS" -eq 0 ]; then
    echo "Releve OK."
else
    echo "Releve en erreur (code $STATUS)."
fi

# Tests unitaires : un echec n'empeche pas le demarrage du serveur.
echo "== Tests unitaires =="
"$PY" test_claude_usage.py || echo "Attention : des tests ont echoue."

# Serveur en arriere-plan, ouvre le navigateur.
echo "== Demarrage du serveur =="
mkdir -p data
nohup "$PY" server.py --open >> data/server.log 2>&1 &
echo "Serveur lance (journal : $ROOT/data/server.log)."
echo "Widget : http://127.0.0.1:8765/"

exit "$STATUS"
