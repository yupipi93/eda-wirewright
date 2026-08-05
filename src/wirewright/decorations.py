"""Non-electrical adornments: legend, free-text notes, dashed annotations. These
are plain draw(painter) callables added to Schematic.decorations."""
from __future__ import annotations

import math

from .library import C


def legend(x, y, w, h, entries, notes=()):
    """entries: list of (color, title, [rows...]); notes: list of str | (str,color)."""
    def draw(p):
        p.rrect((x, y, x + w, y + h), 12, fill=(255, 255, 255), outline=C["outline"], width=2)
        p.text((x + 22, y + 16), "Wire colour → function", font="leg", fill=C["text"], anchor="lt")
        col_w = w // 2
        half = (len(entries) + 1) // 2
        for col in range(2):
            ly = y + 56
            bx = x + 24 + col * col_w
            for col_c, title, rows in entries[col * half:(col + 1) * half]:
                p.rect((bx, ly + 4, bx + 44, ly + 22), fill=col_c, outline=C["outline"], width=1)
                p.text((bx + 58, ly), title, font="leg", fill=C["text"], anchor="lt")
                ly += 28
                for r in rows:
                    p.text((bx + 58, ly), r, font="legsm", fill=C["text"], anchor="lt")
                    ly += 21
                ly += 8
        ly = y + h - 18 - 22 * len(notes)
        for n in notes:
            txt, colr = n if isinstance(n, tuple) else (n, C["text"])
            p.text((x + 22, ly), txt, font="legsm", fill=colr, anchor="lt")
            ly += 22
    return draw


def panel(x, y, w, h, title, rows, accent=None):
    """A titled text box for prose that belongs ON the drawing rather than in the
    legend — a mode table, a build warning, an operating note.

    `rows` items: `""` (blank line) · `("h", text)` (sub-heading, accent colour)
    · `text` or `(text, colour)` (body line).
    """
    def draw(p):
        p.rrect((x, y, x + w, y + h), 12, fill=(255, 255, 255),
                outline=C["outline"], width=2)
        p.rrect((x, y, x + w, y + 6), 3, fill=accent or C["outline"])
        p.text((x + 20, y + 20), title, font="leg", fill=C["text"], anchor="lt")
        ly = y + 58
        for r in rows:
            if not r:
                ly += 12
                continue
            if isinstance(r, tuple) and r[0] == "h":
                p.text((x + 20, ly), r[1], font="leg", fill=accent or C["text"], anchor="lt")
                ly += 26
                continue
            txt, colr = r if isinstance(r, tuple) else (r, C["text"])
            p.text((x + 20, ly), txt, font="legsm", fill=colr, anchor="lt")
            ly += 21
    return draw


def note(x, y, text, color=None, font="pinsm", anchor="lm"):
    color = color or C["text"]
    return lambda p: p.text((x, y), text, font=font, fill=color, anchor=anchor)


def dashed_arrow(x0, y0, x1, y1, color, label=None, w=3, dash=15, gap=11):
    def draw(p):
        dx, dy = x1 - x0, y1 - y0
        dist = math.hypot(dx, dy)
        if dist:
            ux, uy = dx / dist, dy / dist
            n = int(dist // (dash + gap)) + 1
            for i in range(n):
                s = i * (dash + gap); e = min(s + dash, dist)
                p.line([(x0 + ux * s, y0 + uy * s), (x0 + ux * e, y0 + uy * e)], fill=color, width=w)
        if label:
            p.text((x0 + 16, (y0 + y1) / 2), label, font="pinsm", fill=color, anchor="lm")
    return draw
