#!/usr/bin/env python3
"""Build the launchers without `make` (handy on Windows):   python tools/build.py [windows|linux|all]

Needs `pip install ziglang`. Same result as `make`."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def zig(target, out, *sources):
    (ROOT / "bin").mkdir(exist_ok=True)
    cmd = [sys.executable, "-m", "ziglang", "cc", "-target", target] + (["-municode"] if "windows" in target else []) + ["-Os", "-s", "-o", str(ROOT / "bin" / out)] + [str(ROOT / s) for s in sources]
    print(" ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("windows", "all"):
        zig("x86_64-windows-gnu", "claude-usage-tracker.exe", "tools/launcher.c", "assets/app.rc")
    if what in ("linux", "all"):
        zig("x86_64-linux-musl", "claude-usage-tracker", "tools/launcher.c")


if __name__ == "__main__":
    main()
