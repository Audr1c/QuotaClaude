# -*- coding: utf-8 -*-
"""Tiny terminal UI: arrow-key menus that work on Windows and Linux, standard library only.

If the terminal cannot do it (output piped, very old console, no TTY), everything falls back
to plain numbered prompts, so the launcher still works over SSH, in CI, or when scripted.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import sys
import textwrap

ESC = "\x1b"
RESET = ESC + "[0m"
BOLD = ESC + "[1m"
DIM = ESC + "[2m"
ORANGE = ESC + "[38;5;173m"      # close to the Claude orange
HIDE_CURSOR = ESC + "[?25l"
SHOW_CURSOR = ESC + "[?25h"

_interactive: bool | None = None


def _enable_windows_ansi() -> bool:
    """Turn on ANSI escape processing in the Windows console (Windows 10+). False if impossible."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        return False


def interactive() -> bool:
    """True when we can draw arrow-key menus."""
    global _interactive
    if _interactive is None:
        ok = sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get("TERM") != "dumb"
        if ok and os.name == "nt":
            ok = _enable_windows_ansi()
        _interactive = ok
    return _interactive


def _style(code: str, text: str) -> str:
    return text if os.environ.get("NO_COLOR") else f"{code}{text}{RESET}"


def _width() -> int:
    return max(30, min(shutil.get_terminal_size((80, 24)).columns - 2, 100))


def _fit(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


# --------------------------------------------------------------------------- keyboard

@contextlib.contextmanager
def _keyboard():
    """Single-key mode for the duration of a menu (POSIX; Windows already reads single keys).

    Set once per menu, not once per key: switching modes can discard keys typed ahead
    (for example an arrow key held down).
    """
    if os.name == "nt":
        yield
        return
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd, termios.TCSANOW)               # keeps Ctrl+C working, does not flush input
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_key() -> str:
    """Return 'up', 'down', 'enter', 'esc', or the typed character (lower-cased). Raises KeyboardInterrupt on Ctrl+C."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):                      # special key: the real code follows
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x1b":
            return "esc"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch.lower()

    import select
    fd = sys.stdin.fileno()
    data = os.read(fd, 1)
    if data == b"\x1b" and select.select([fd], [], [], 0.05)[0]:
        nxt = os.read(fd, 1)
        data += nxt
        if nxt in (b"[", b"O"):                          # arrow keys etc.: read up to the final byte of the sequence
            while True:
                b = os.read(fd, 1)
                data += b
                if not b or 0x40 <= b[0] <= 0x7E:
                    break
    if data.startswith((b"\x1b[", b"\x1bO")) and data.endswith(b"A"):
        return "up"
    if data.startswith((b"\x1b[", b"\x1bO")) and data.endswith(b"B"):
        return "down"
    if data == b"\x1b":
        return "esc"
    if data in (b"\r", b"\n"):
        return "enter"
    if data == b"\x03":
        raise KeyboardInterrupt
    return data.decode("utf-8", "ignore").lower() if not data.startswith(b"\x1b") else ""


# --------------------------------------------------------------------------- menus

def choose(title: str, options: list[tuple[str, str]], *, hint: str, plain_hint: str = "",
           intro: str = "", selected: int = 0) -> int | None:
    """Show a menu; options are (label, description). Returns the chosen index, or None for Esc / q."""
    if not interactive():
        return _choose_plain(title, options, plain_hint or hint, intro)

    width = _width()
    wrapped = [textwrap.wrap(desc, width - 2) or [""] for _, desc in options]
    desc_height = max(len(w) for w in wrapped)           # constant height: the menu never "jumps"
    intro_lines = textwrap.wrap(intro, width) if intro else []

    def render(idx: int) -> list[str]:
        out = [_style(BOLD + ORANGE, _fit(title, width))]
        out += [_style(DIM, line) for line in intro_lines]
        out.append("")
        for i, (label, _) in enumerate(options):
            num = f"{i + 1}." if i < 9 else "  "
            text = _fit(f"{num} {label}", width - 2)
            out.append(f"{_style(ORANGE, '›')} {_style(BOLD, text)}" if i == idx else f"  {text}")
        out.append("")
        lines = wrapped[idx] + [""] * (desc_height - len(wrapped[idx]))
        out += [_style(DIM, "  " + line) for line in lines]
        out.append("")
        out.append(_style(DIM, _fit(hint, width)))
        return out

    idx = min(max(selected, 0), len(options) - 1)
    block = render(idx)
    height = len(block)
    out = sys.stdout
    result: int | None = None
    try:
        with _keyboard():
            out.write(HIDE_CURSOR + "\n".join(block) + "\n")
            out.flush()
            while True:
                key = read_key()
                if key == "up":
                    idx = (idx - 1) % len(options)
                elif key == "down":
                    idx = (idx + 1) % len(options)
                elif key == "enter":
                    result = idx
                    break
                elif key in ("esc", "q"):
                    break
                elif key.isdigit() and 1 <= int(key) <= min(9, len(options)):
                    result = int(key) - 1
                    break
                else:
                    continue
                out.write(f"{ESC}[{height}A{ESC}[J" + "\n".join(render(idx)) + "\n")
                out.flush()
    finally:
        out.write(f"{ESC}[{height}A{ESC}[J" + SHOW_CURSOR)   # erase the menu, restore the cursor
        out.flush()
    if result is not None:
        out.write(f"{_style(ORANGE, '›')} {options[result][0]}\n")
        out.flush()
    return result


def _choose_plain(title: str, options: list[tuple[str, str]], hint: str, intro: str) -> int | None:
    print(title)
    if intro:
        print(intro)
    for i, (label, desc) in enumerate(options, 1):
        print(f"  {i}) {label} - {desc}")
    print(hint)
    while True:
        try:
            raw = input("> ").strip().lower()
        except EOFError:
            return None
        if raw in ("q", "quit", "exit"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1


def ask(prompt: str, default: str = "") -> str:
    """Read a line; returns `default` when the user just presses Enter (or when input is closed)."""
    try:
        value = input(prompt).strip()
    except EOFError:
        return default
    return value or default


def pause(message: str) -> None:
    if sys.stdin.isatty():
        try:
            input(message)
        except EOFError:
            pass
