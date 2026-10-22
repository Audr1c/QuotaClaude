#!/usr/bin/env python3
"""Build the launchers and icons (what `make` calls).   python tools/build.py [all|windows|linux|icons|desktop|clean]

Needs `pip install ziglang` (and `pip install pillow` for the icons). Pure Python: works on Windows, Linux, macOS."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"


def zig(target, out, *sources):
    BIN.mkdir(exist_ok=True)
    cmd = [sys.executable, "-m", "ziglang", "cc", "-target", target] + (["-municode"] if "windows" in target else []) \
        + ["-Os", "-s", "-o", str(BIN / out)] + [str(ROOT / s) for s in sources]
    print(" ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def desktop():
    """Install a Linux applications-menu entry pointing at this folder."""
    home = Path.home()
    apps, icons = home / ".local/share/applications", home / ".local/share/icons"
    apps.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    icon = icons / "claude-usage-tracker.png"
    shutil.copy(ROOT / "assets" / "icon-256.png", icon)
    text = (ROOT / "linux" / "claude-usage-tracker.desktop.in").read_text(encoding="utf-8")
    text = text.replace("@DIR@", str(ROOT)).replace("@ICON@", str(icon))
    (apps / "claude-usage-tracker.desktop").write_text(text, encoding="utf-8")
    print("Menu entry installed: Claude Usage Tracker")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("windows", "all"):
        zig("x86_64-windows-gnu", "claude-usage-tracker.exe", "tools/launcher.c", "assets/app.rc")
    if what in ("linux", "all"):
        zig("x86_64-linux-musl", "claude-usage-tracker", "tools/launcher.c")
    if what == "icons":
        subprocess.check_call([sys.executable, str(ROOT / "tools" / "make_icons.py")])
    if what == "desktop":
        zig("x86_64-linux-musl", "claude-usage-tracker", "tools/launcher.c")
        desktop()
    if what == "clean":
        shutil.rmtree(BIN, ignore_errors=True)
    if what not in ("all", "windows", "linux", "icons", "desktop", "clean"):
        sys.exit(f"unknown target: {what}")


if __name__ == "__main__":
    main()
