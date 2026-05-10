#!/usr/bin/env python3
"""Cross-platform launcher for Batman Returns (Python).

Run from anywhere::

    python play.py

If pygame-ce / numpy aren't installed, this script prints a clear, one-line
install command instead of a stack trace, and offers to install them for you.

If you prefer the one-click experience, use ``run.bat`` (Windows) or
``run.sh`` (macOS / Linux) instead — they create a virtualenv automatically.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

REQUIRED = ("pygame", "numpy")
PIP_NAME = {"pygame": "pygame-ce", "numpy": "numpy"}


def _check_python_version() -> None:
    # The runtime check is intentional even though pyproject.toml gates on
    # 3.11+ — play.py is meant to be run by a user who hasn't installed yet.
    if sys.version_info < (3, 11):  # noqa: UP036
        print(
            f"\n[ERROR] Batman Returns needs Python 3.11+, you have "
            f"{sys.version_info.major}.{sys.version_info.minor}.\n"
            "  Install a newer Python from https://www.python.org/downloads/\n"
        )
        sys.exit(1)


def _check_deps() -> list[str]:
    missing: list[str] = []
    for mod in REQUIRED:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(PIP_NAME[mod])
    return missing


def _maybe_install(missing: list[str]) -> None:
    pip_args = [sys.executable, "-m", "pip", "install", *missing]
    print("\nMissing dependencies:")
    for pkg in missing:
        print(f"  - {pkg}")
    print("\nI can install them for you with:")
    print(f"  {' '.join(pip_args)}\n")
    try:
        ans = input("Install now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    if ans in ("", "y", "yes", "s", "si"):
        rc = subprocess.call(pip_args)
        if rc != 0:
            print("\n[ERROR] pip install failed. Try manually:")
            print(f"  {' '.join(pip_args)}")
            sys.exit(rc)
    else:
        print("\nInstall manually and re-run play.py")
        sys.exit(1)


def main() -> int:
    _check_python_version()
    # Make sure src/ is on the import path so the launcher works pre-install.
    here = Path(__file__).resolve().parent
    src = here / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    missing = _check_deps()
    if missing:
        _maybe_install(missing)
        # Re-check after install
        missing = _check_deps()
        if missing:
            print(f"\n[ERROR] Still missing: {missing}")
            return 1

    # Import + run
    from batman_returns.__main__ import main as game_main
    return game_main()


if __name__ == "__main__":
    raise SystemExit(main())
