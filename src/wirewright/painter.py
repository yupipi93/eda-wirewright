"""Thin drawing layer over PIL — fonts, primitives, text metrics. Components and
the engine draw through a Painter so the rest of the engine never touches PIL
directly (makes it swappable and keeps draw code declarative)."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans{bold}.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans{reg}.ttf",
]


def _load(size, bold=False):
    for tmpl in _FONT_PATHS:
        path = tmpl.format(bold="-Bold" if bold else "",
                           reg="-Bold" if bold else "-Regular")
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# Named font registry — components reference fonts by key, never by raw size, so
# the whole diagram restyles from one place.
FONTS = {
    "title":  _load(42, bold=True),
    "sub":    _load(23),
    "mod":    _load(28, bold=True),
    "modsub": _load(17),
    "pin":    _load(16, bold=True),
    "pinsm":  _load(14, bold=True),
    "leg":    _load(21, bold=True),
    "legsm":  _load(16),
    "tiny":   _load(13),
}


def measure_box(x, y, s, font="pinsm", anchor="lm", pad=3):
    """The pixel AABB a piece of text will occupy — computed at construction time
    (no painter needed) so label areas can be handed to the router as obstacles."""
    from .geometry import BBox
    f = FONTS[font]
    b = f.getbbox(s)
    w, h = b[2] - b[0], b[3] - b[1]
    ah, av = anchor[0], anchor[1]
    x0 = x if ah == "l" else (x - w / 2 if ah == "m" else x - w)
    y0 = y if av in ("t", "a") else (y - h / 2 if av == "m" else y - h)
    return BBox(x0 - pad, y0 - pad, x0 + w + pad, y0 + h + pad)


class Painter:
    def __init__(self, w, h, bg=(250, 250, 248)):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w, h), bg)
        self.d = ImageDraw.Draw(self.img)

    # ---- text ----
    def text(self, xy, s, font="pin", fill=(25, 25, 30), anchor="lm"):
        self.d.text(xy, s, font=FONTS[font], fill=fill, anchor=anchor)

    def text_size(self, s, font="pin"):
        b = FONTS[font].getbbox(s)
        return b[2] - b[0], b[3] - b[1]

    def text_bbox(self, xy, s, font="pin", anchor="lm"):
        """Absolute (x0,y0,x1,y1) a piece of text will occupy — for label DRC."""
        x0, y0, x1, y1 = self.d.textbbox(xy, s, font=FONTS[font], anchor=anchor)
        return (x0, y0, x1, y1)

    # ---- shapes ----
    def line(self, pts, fill, width=5):
        self.d.line(pts, fill=fill, width=width)

    def rect(self, box, fill=None, outline=None, width=1):
        self.d.rectangle(box, fill=fill, outline=outline, width=width)

    def rrect(self, box, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        self.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=width)

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse(box, fill=fill, outline=outline, width=width)

    def dot(self, cx, cy, r, fill, outline=(40, 40, 50), width=1):
        self.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=width)

    def save(self, path):
        self.img.save(path)
