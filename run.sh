#!/bin/sh
# Linux/macOS launcher: finds Python 3.8+ and starts the interactive menu.
# Usage: ./run.sh [command]   (or: sh run.sh, python3 run.py)
cd "$(dirname "$0")" || exit 1
for py in python3 python; do
    if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
        exec "$py" run.py "$@"
    fi
done
echo "Python 3.8 or newer was not found. Install it (for example: sudo apt install python3) and try again." >&2
exit 1
