# -*- coding: utf-8 -*-
"""Start-up banner: the twin-rings logo drawn with half-block characters (two pixels per terminal cell)."""
from __future__ import annotations

import math
import os
import sys

CLAY, BLUE, TRACK = (217, 119, 87), (106, 155, 204), (74, 72, 66)
SIZE = 22                                    # pixels; 11 terminal rows


def _pixels() -> list[list[tuple | None]]:
    grid: list[list] = [[None] * SIZE for _ in range(SIZE)]
    c = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x - c, y - c)
            a = (math.degrees(math.atan2(y - c, x - c)) - 135) % 360
            if a > 270:
                continue
            for radius, end, color in ((9.6, 165, CLAY), (5.6, 115, BLUE)):   # outer = week, inner = 5 hours
                if abs(r - radius) <= 1.55:
                    grid[y][x] = color if a <= end else TRACK
    return grid


def logo_lines(color: bool = True) -> list[str]:
    grid = _pixels()
    lines = []
    for y in range(0, SIZE, 2):
        out = ""
        for x in range(SIZE):
            top, bottom = grid[y][x], grid[y + 1][x]
            if not color:
                out += "█" if top or bottom else " "
                continue
            fg = f"\x1b[38;2;{top[0]};{top[1]};{top[2]}m" if top else ""
            bg = f"\x1b[48;2;{bottom[0]};{bottom[1]};{bottom[2]}m" if bottom else ""
            if top or bottom:
                out += f"{fg}{bg}▀\x1b[0m" if top else f"\x1b[38;2;{bottom[0]};{bottom[1]};{bottom[2]}m▄\x1b[0m"
            else:
                out += " "
        lines.append(out)
    return lines


def show(title: str, tagline: str) -> None:
    """Print the banner once. Plain text when colours are unavailable."""
    colour = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    try:
        art = logo_lines(colour)
        "█▀▄".encode(sys.stdout.encoding or "utf-8")
    except Exception:
        print(f"\n  {title}\n  {tagline}\n")
        return
    text = {3: f"\x1b[1m{title}\x1b[0m" if colour else title, 5: f"\x1b[2m{tagline}\x1b[0m" if colour else tagline}
    print()
    for i, line in enumerate(art):
        print("  " + line + "   " + text.get(i, ""))
    print()
