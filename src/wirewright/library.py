"""Component library — factories that place a body + typed ports at an anchor and
return a Component the engine can route to. Each factory owns ONLY its own body
and labels; wires are the engine's job.

Every factory returns a Component whose ports face the direction their wire
should leave (so the router's escape stub is always perpendicular to the body)."""
from __future__ import annotations

from .geometry import BBox
from .model import Component, Port
from .painter import measure_box
from .theme import C


class LabelBag:
    """Collects a component's EXTERNAL text once, so the same specs drive both
    drawing and the obstacle boxes handed to the router (no drift)."""
    def __init__(self):
        self.items = []

    def add(self, x, y, s, font="pinsm", anchor="lm", color=None, soft=True):
        # soft=False -> drawn but NOT an obstacle (e.g. text sitting over its own
        # port's escape wire, where blocking would force an ugly detour)
        self.items.append((x, y, s, font, anchor, color if color is not None else C["text"], soft))

    def draw(self, p):
        for (x, y, s, f, a, col, _s) in self.items:
            p.text((x, y), s, font=f, fill=col, anchor=a)

    def boxes(self):
        return [measure_box(x, y, s, f, a) for (x, y, s, f, a, _c, soft) in self.items if soft]

PIN_R = 8


def _pin(p, x, y, hi=False):
    p.circle(x, y, PIN_R, fill=(255, 255, 255) if hi else C["pinfill"],
             outline=C["outline"], width=2)


# ── Arduino Nano ─────────────────────────────────────────────────────────────
NANO_W, NANO_H = 300, 600
LEFT = ["VIN", "GND", "RST", "5V", "A7", "A6", "A5", "A4",
        "A3", "A2", "A1", "A0", "AREF", "3V3", "D13"]
RIGHT = ["TX1", "RX0", "RST2", "GND2", "D2", "D3", "D4", "D5",
         "D6", "D7", "D8", "D9", "D10", "D11", "D12"]
LABELS = {"RST2": "RST", "GND2": "GND", "TX1": "D1/TX", "RX0": "D0/RX"}


def arduino_nano(id, x, y, board="ATmega328P · Nano / Uno"):
    x0, y0 = x, y
    x1, y1 = x + NANO_W, y + NANO_H
    body = BBox(x0, y0, x1, y1)
    pin_top = y0 + 44
    step = (NANO_H - 88) / 14.0
    ports = {}
    for i, nm in enumerate(LEFT):
        ports[nm] = Port(nm, x0, int(pin_top + i * step), "W")
    for i, nm in enumerate(RIGHT):
        ports[nm] = Port(nm, x1, int(pin_top + i * step), "E")

    def draw(p):
        cxn = x0 + NANO_W // 2
        p.rrect((x0, y0, x1, y1), 12, fill=C["nano"], outline=C["outline"], width=3)
        p.rrect((cxn - 52, y0 - 26, cxn + 52, y0 + 6), 6, fill=(205, 205, 210),
                outline=C["outline"], width=2)
        p.text((cxn, y0 - 34), "mini-USB", font="modsub", fill=C["text"], anchor="mb")
        p.text((cxn, y0 + NANO_H // 2 - 16), "Arduino", font="mod", fill=C["light"], anchor="mm")
        p.text((cxn, y0 + NANO_H // 2 + 18), "NANO", font="mod", fill=C["light"], anchor="mm")
        p.text((cxn, y1 + 22), board, font="modsub", fill=C["text"], anchor="mt")
        for nm in LEFT:
            pt = ports[nm]; _pin(p, pt.x, pt.y)
            p.text((pt.x + 15, pt.y), LABELS.get(nm, nm), font="pin", fill=C["light"], anchor="lm")
        for nm in RIGHT:
            pt = ports[nm]; _pin(p, pt.x, pt.y)
            p.text((pt.x - 15, pt.y), LABELS.get(nm, nm), font="pin", fill=C["light"], anchor="rm")

    return Component(id, body, ports, draw, clearance=16)


# ── lemon touch key ──────────────────────────────────────────────────────────
def lemon_key(id, x, y, keynum, apin):
    body = BBox(x - 46, y - 34, x + 52, y + 34)
    ports = {"clip": Port("clip", x + 52, y, "E")}

    def draw(p):
        p.ellipse((x - 46, y - 34, x + 46, y + 34), fill=C["lemon"], outline=C["lemon_edge"], width=3)
        p.ellipse((x + 30, y - 6, x + 52, y + 10), fill=C["lemon"], outline=C["lemon_edge"], width=2)
        p.text((x, y - 8), f"Key {keynum}", font="pin", fill=C["text"], anchor="mm")
        p.text((x, y + 12), apin, font="pinsm", fill=C["text"], anchor="mm")

    return Component(id, body, ports, draw, clearance=12)


# ── resistor (2-terminal) ────────────────────────────────────────────────────
def resistor(id, x, y, orient="H", label="220 Ω", length=68):
    half = length / 2
    bag = LabelBag()
    if orient == "H":
        body = BBox(x - half, y - 15, x + half, y + 15)
        ports = {"a": Port("a", x - half, y, "W"), "b": Port("b", x + half, y, "E")}
        bag.add(x, y - 30, label, "pinsm", "mm")

        def draw(p):
            p.rrect((x - half, y - 14, x + half, y + 14), 7, fill=C["res"], outline=C["outline"], width=3)
            bag.draw(p)
    else:
        body = BBox(x - 15, y - half, x + 15, y + half)
        ports = {"a": Port("a", x, y - half, "N"), "b": Port("b", x, y + half, "S")}
        bag.add(x - 18, y, label, "tiny", "rm")

        def draw(p):
            p.rrect((x - 13, y - half, x + 13, y + half), 6, fill=C["res"], outline=C["outline"], width=3)
            bag.draw(p)

    return Component(id, body, ports, draw, clearance=10, label_boxes=bag.boxes())


# ── LED ──────────────────────────────────────────────────────────────────────
def led(id, x, y, color, label, sub, r=20, anode="N", cathode="S"):
    """anode/cathode facings default to N/S (bus up, drop to GND). Set anode='W'
    when the LED is driven from a pin to its left so the wire enters straight."""
    body = BBox(x - r, y - r, x + r, y + r)
    _fp = {"N": (x, y - r), "S": (x, y + r), "W": (x - r, y), "E": (x + r, y)}
    ports = {"anode": Port("anode", *_fp[anode], anode),
             "cathode": Port("cathode", *_fp[cathode], cathode)}
    bag = LabelBag()
    bag.add(x + r + 12, y - 9, label, "pinsm", "lm")
    if sub:
        bag.add(x + r + 12, y + 10, sub, "tiny", "lm", C["muted"])

    def draw(p):
        p.circle(x, y, r, fill=color, outline=C["outline"], width=3)
        p.line([(x - 14, y - 18), (x - 28, y - 32)], fill=C["outline"], width=2)
        p.line([(x - 22, y - 10), (x - 36, y - 24)], fill=C["outline"], width=2)
        bag.draw(p)

    return Component(id, body, ports, draw, clearance=12, label_boxes=bag.boxes())


# ── passive buzzer ───────────────────────────────────────────────────────────
def buzzer(id, x, y, r=32):
    body = BBox(x - r, y - r, x + r, y + r)
    ports = {"sig": Port("sig", x, y - r, "N"), "gnd": Port("gnd", x, y + r, "S")}
    bag = LabelBag()
    bag.add(x, y + r + 6, "passive buzzer", "pinsm", "mt")
    bag.add(x, y + r + 24, "D8", "tiny", "mt", C["muted"])

    def draw(p):
        p.circle(x, y, r, fill=C["buzz_body"], outline=C["outline"], width=3)
        p.circle(x, y, 8, fill=(90, 90, 96), outline=C["outline"], width=2)
        bag.draw(p)

    return Component(id, body, ports, draw, clearance=12, label_boxes=bag.boxes())


# ── push button (active-HIGH) ────────────────────────────────────────────────
def push_button(id, x, y, label, sub, cap=(180, 60, 60), hw=30):
    body = BBox(x - hw, y - hw, x + hw, y + hw)
    ports = {"pin": Port("pin", x - hw, y, "W"), "v5": Port("v5", x + hw, y, "E")}
    bag = LabelBag()
    bag.add(x, y + hw + 6, label, "pinsm", "mt")
    if sub:
        bag.add(x, y + hw + 24, sub, "tiny", "mt", C["muted"])

    def draw(p):
        p.rrect((x - hw, y - hw, x + hw, y + hw), 9, fill=C["btn"], outline=C["outline"], width=3)
        p.circle(x, y, 15, fill=cap, outline=C["outline"], width=2)
        bag.draw(p)

    return Component(id, body, ports, draw, clearance=12, label_boxes=bag.boxes())


# ── SPDT game-select switch ──────────────────────────────────────────────────
def spdt_switch(id, x, y, pin_label, com_facing="W", analog=False):
    w2, h2 = 56, 36
    body = BBox(x - w2, y - h2, x + w2, y + h2)
    com_x = x - w2 if com_facing == "W" else x + w2
    ports = {
        "com": Port("com", com_x, y, com_facing),
        "p5": Port("p5", x, y - h2, "N"),
        "pg": Port("pg", x, y + h2, "S"),
    }
    bag = LabelBag()
    bag.add(x, y - h2 - 10, "GAME SELECT (SPDT)", "pinsm", "mb", soft=False)
    bag.add(x + w2 + 8, y - h2 + 10, "g1 = 5V", "tiny", "lm", (150, 40, 40))
    bag.add(x + w2 + 8, y + h2 - 10, "g2 = GND", "tiny", "lm", (60, 60, 66))
    if analog:
        bag.add(x, y + h2 + 24, "* A7 is analog-in only", "tiny", "mt", C["muted"])

    def draw(p):
        p.rrect((x - w2, y - h2, x + w2, y + h2), 10, fill=C["btn"], outline=C["outline"], width=3)
        _pin(p, x, y - h2, hi=True); _pin(p, x, y + h2, hi=True); _pin(p, com_x, y, hi=True)
        p.line([(x, y + 6), (x, y - h2)], fill=(230, 230, 235), width=5)
        p.text((x, y), pin_label + ("*" if analog else ""), font="tiny", fill=C["light"], anchor="mm")
        bag.draw(p)

    return Component(id, body, ports, draw, clearance=12, label_boxes=bag.boxes())


# ── 2-channel relay module ───────────────────────────────────────────────────
def relay_module(id, x, y, w2=84):
    body = BBox(x - w2, y - 58, x + w2, y + 58)
    ports = {
        "IN1": Port("IN1", x - 44, y + 58, "S"),
        "IN2": Port("IN2", x + 44, y + 58, "S"),
        "VCC": Port("VCC", x - w2, y - 34, "W"),
        "GND": Port("GND", x - w2, y + 4, "W"),
        "OUT": Port("OUT", x, y + 58, "S"),
    }

    def draw(p):
        p.rrect((x - w2, y - 58, x + w2, y + 58), 10, fill=C["relay_body"], outline=C["outline"], width=3)
        p.text((x, y - 32), "RELAY ×2", font="pin", fill=C["light"], anchor="mm")
        p.text((x, y - 8), "module", font="pinsm", fill=C["light"], anchor="mm")
        for nm, dx in (("IN1", -44), ("IN2", 44)):
            _pin(p, x + dx, y + 58, hi=True)
            p.text((x + dx, y + 38), nm, font="tiny", fill=C["light"], anchor="mm")
        _pin(p, x - w2, y - 34); _pin(p, x - w2, y + 4)
        p.text((x - w2 - 8, y - 34), "V+", font="tiny", fill=C["text"], anchor="rm")
        p.text((x - w2 - 8, y + 4), "G", font="tiny", fill=C["text"], anchor="rm")

    return Component(id, body, ports, draw, clearance=14)


# ── water pump ───────────────────────────────────────────────────────────────
def water_pump(id, x, y):
    body = BBox(x - 66, y - 38, x + 66, y + 38)
    ports = {"in": Port("in", x, y - 38, "N")}
    bag = LabelBag()
    bag.add(x, y + 44, "sprays you on a late miss", "tiny", "mt", (190, 90, 90))

    def draw(p):
        p.rrect((x - 66, y - 38, x + 66, y + 38), 10, fill=C["pump"], outline=C["outline"], width=3)
        p.text((x, y - 11), "WATER", font="pin", fill=C["light"], anchor="mm")
        p.text((x, y + 13), "PUMP", font="pin", fill=C["light"], anchor="mm")
        bag.draw(p)

    return Component(id, body, ports, draw, clearance=12, label_boxes=bag.boxes())


# ── hand-held 5V clip (player) ───────────────────────────────────────────────
def clip_box(id, x, y):
    body = BBox(x, y, x + 300, y + 92)
    ports = {"out": Port("out", x + 300, y + 46, "E")}

    def draw(p):
        p.rrect((x, y, x + 300, y + 92), 12, fill=(250, 244, 200), outline=C["lemon_edge"], width=3)
        p.text((x + 150, y + 24), "hand-held 5 V clip", font="mod", fill=C["text"], anchor="mm")
        p.text((x + 150, y + 60), "held in one hand = the player", font="modsub", fill=C["text"], anchor="mm")

    return Component(id, body, ports, draw, clearance=10, is_obstacle=True)
