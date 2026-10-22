#!/usr/bin/env bash
# Ouvre le widget : demarre le serveur, ou ouvre seulement le navigateur s'il tourne deja.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
    echo "Erreur : python3 (ou python) introuvable. Installez Python 3." >&2
    exit 1
fi

mkdir -p data
nohup "$PY" server.py --open >> data/server.log 2>&1 &
echo "Widget : http://127.0.0.1:8765/"
