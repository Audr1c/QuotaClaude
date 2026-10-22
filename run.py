#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Usage Tracker - start here.

    python run.py              interactive menu (works on Windows and Linux)
    python run.py --help       command-line shortcuts: read, open, stop, status, install, uninstall, tests

On Windows you can also double-click run.bat; on Linux run ./run.sh.
"""
import sys

if sys.version_info < (3, 8):
    sys.exit("Python 3.8 or newer is required (found %d.%d)." % sys.version_info[:2])

from launcher.app import main  # noqa: E402  (after the version check, so old Pythons get a clear message)

if __name__ == "__main__":
    sys.exit(main())
