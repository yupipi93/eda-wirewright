"""Colour palette + resolver. Nets and rails may name a palette colour
("led", "gnd", …), pass a hex string ("#ff0000") or an [r,g,b] triple — the
resolver turns any of those into an (r,g,b) tuple. Keeping the palette here
(not in library) makes it swappable for a different visual theme."""
from __future__ import annotations

# functional wire colours (each == one function, keyed for legends)
PALETTE = {
    "v5": (215, 40, 40),      # red    — +5 V
    "gnd": (35, 35, 40),      # black  — ground
    "key": (35, 165, 75),     # green  — analog key / sense lines
    "led": (40, 110, 220),    # blue   — LED / signal drive
    "ctrl": (235, 140, 20),   # orange — control lines
    "buzz": (150, 60, 200),   # purple — buzzer / audio
    "relay": (150, 100, 40),  # brown  — relay / actuator drive
    "margin": (220, 60, 150), # pink   — secondary controls
    "sig": (40, 110, 220),    # alias of led (generic signal)
    "power": (215, 40, 40),   # alias of v5
}

# component/body colours
BODY = {
    "nano": (28, 70, 150), "lemon": (232, 214, 60), "lemon_edge": (150, 135, 20),
    "res": (222, 196, 150), "btn": (60, 60, 66), "relay_body": (70, 66, 78),
    "pump": (60, 90, 140), "buzz_body": (40, 40, 46),
    "text": (25, 25, 30), "light": (252, 252, 250), "outline": (40, 40, 50),
    "pinfill": (245, 235, 110), "muted": (110, 110, 116),
}

# backward-compatible flat dict used throughout the library
C = {**PALETTE, **BODY}

# common English/Spanish colour names for the declarative format
_NAMED = {
    "red": (215, 40, 40), "green": (45, 185, 75), "blue": (40, 110, 220),
    "black": (35, 35, 40), "white": (252, 252, 250), "orange": (235, 140, 20),
    "purple": (150, 60, 200), "brown": (150, 100, 40), "pink": (220, 60, 150),
    "yellow": (232, 214, 60), "grey": (110, 110, 116), "gray": (110, 110, 116),
    "rojo": (215, 40, 40), "verde": (45, 185, 75), "azul": (40, 110, 220),
    "negro": (35, 35, 40), "naranja": (235, 140, 20), "morado": (150, 60, 200),
}


def resolve_color(v):
    """Accept an (r,g,b) tuple/list, a '#rrggbb' hex, or a name (palette or common
    colour). Returns an (r,g,b) int tuple."""
    if isinstance(v, (tuple, list)) and len(v) == 3:
        return tuple(int(c) for c in v)
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("#") and len(s) == 7:
            return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
        if s in C:
            return C[s]
        if s.lower() in _NAMED:
            return _NAMED[s.lower()]
    raise ValueError(f"cannot resolve colour {v!r} "
                     f"(use an [r,g,b], '#rrggbb', or a palette/colour name)")
