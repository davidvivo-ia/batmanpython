#!/usr/bin/env bash
# ======================================================================
# Batman Returns (Python) — one-click launcher for macOS / Linux
#
# Run with:  ./run.sh
# Or:        bash run.sh
#
# Steps automatically:
#   1. Find Python 3.11+
#   2. Create venv in ./.venv on first run
#   3. Install game in editable mode
#   4. Launch the game
# ======================================================================

set -euo pipefail
cd "$(dirname "$0")"

# ---- Find a usable Python ----
PYEXE=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        # Verify it's at least 3.11
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            PYEXE="$candidate"
            break
        fi
    fi
done

if [ -z "$PYEXE" ]; then
    echo
    echo "[ERROR] No Python 3.11+ found on PATH."
    echo "  Install Python 3.11 or newer from https://www.python.org/downloads/"
    echo "  (macOS users can also: brew install python@3.13)"
    echo
    exit 1
fi

# ---- Create venv on first run ----
if [ ! -x ".venv/bin/python" ]; then
    echo "First run: creating virtual environment in .venv/ ..."
    "$PYEXE" -m venv .venv
    echo "Installing dependencies (pygame-ce, numpy) ..."
    .venv/bin/python -m pip install --quiet --upgrade pip
    .venv/bin/python -m pip install --quiet -e .
fi

# ---- Run the game ----
exec .venv/bin/python -m batman_returns "$@"
