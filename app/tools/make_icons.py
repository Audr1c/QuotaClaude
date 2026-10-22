#!/usr/bin/env python3
"""Generate every icon from one definition (twin rings: orange = week, blue = 5-hour).

    python tools/make_icons.py        needs Pillow (pip install pillow)

Writes assets/icon.svg, assets/icon-<size>.png, assets/icon.ico, web/favicon.svg, web/favicon.png
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
CLAY, BLUE, TRACK, CREAM = "#D97757", "#6A9BCC", "#E3E0D5", "#F0EEE6"

# (centre y, outer radius, inner radius, ring width, end angle of the orange arc, end angle of the blue arc)
TILE = dict(cy=68, r1=44, r2=26, w=11, a1=300, a2=250, tile=True)         # app icon: rounded tile, thin rings
FAVICON = dict(cy=66, r1=50, r2=27, w=19, a1=300, a2=250, tile=False)    # browser tab: bolder, no tile


def arc_path(cx, cy, r, a0, a1):
    p = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = p(a0), p(a1)
    return f"M{x0:.2f} {y0:.2f} A{r} {r} 0 {1 if (a1 - a0) % 360 > 180 else 0} 1 {x1:.2f} {y1:.2f}"


def svg(s):
    ring = lambda r, a, c: (f'<path d="{arc_path(64, s["cy"], r, 135, 405)}" fill="none" stroke="{TRACK}" stroke-width="{s["w"]}" stroke-linecap="round"/>'
                            f'<path d="{arc_path(64, s["cy"], r, 135, a)}" fill="none" stroke="{c}" stroke-width="{s["w"]}" stroke-linecap="round"/>')
    bg = f'<rect width="128" height="128" rx="28" fill="{CREAM}"/>' if s["tile"] else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">{bg}'
            f'{ring(s["r1"], s["a1"], CLAY)}{ring(s["r2"], s["a2"], BLUE)}</svg>\n')


def png(s, size):
    k = 8                                              # supersampling
    n = size * k
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = n / 128
    if s["tile"]:
        d.rounded_rectangle([0, 0, n - 1, n - 1], radius=28 * u, fill=CREAM)

    def stamp(r, a0, a1, color):
        step = 0.25
        a = a0
        while a <= a1 + 1e-9:
            x, y = (64 + r * math.cos(math.radians(a))) * u, (s["cy"] + r * math.sin(math.radians(a))) * u
            d.ellipse([x - s["w"] / 2 * u, y - s["w"] / 2 * u, x + s["w"] / 2 * u, y + s["w"] / 2 * u], fill=color)
            a += step
    for r, a_end, color in ((s["r1"], s["a1"], CLAY), (s["r2"], s["a2"], BLUE)):
        stamp(r, 135, 405, TRACK)
        stamp(r, 135, a_end, color)
    return img.resize((size, size), Image.LANCZOS)


def main():
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets" / "icon.svg").write_text(svg(TILE), encoding="utf-8")
    (ROOT / "web" / "favicon.svg").write_text(svg(FAVICON), encoding="utf-8")
    sizes = (16, 32, 48, 64, 128, 256)
    frames = {n: png(TILE if n >= 48 else FAVICON, n) for n in sizes}   # small sizes use the bolder design
    for n, im in frames.items():
        im.save(ROOT / "assets" / f"icon-{n}.png")
    frames[256].save(ROOT / "assets" / "icon.ico", sizes=[(n, n) for n in sizes], append_images=[frames[n] for n in sizes if n != 256])
    png(FAVICON, 64).save(ROOT / "web" / "favicon.png")
    print("icons written")


if __name__ == "__main__":
    main()
