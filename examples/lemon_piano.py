"""Example: the three Lemon Piano wiring diagrams, built with wirewright.

This file is now just the *contract* for each version: it says which components
exist, where they sit, and what connects to what. All the hard work — routing
orthogonal wires that never cross a component body, never run coincident, never
leave a pin unconnected, and keep their distance — is done by the reusable
`schematic` engine (tools/schematic/), which also DRC-validates every diagram
before saving. See tools/schematic/README.md for the design.

Run:  python3 tools/wiring_diagrams.py
Out:  docs/images/wiring-{v4,v4-plus,v5}.png
"""
from pathlib import Path

from wirewright import Schematic, lib, P, R, Rail, build, save, C, deco

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 3400, 1580
RAIL_5V_Y, RAIL_GND_Y = 360, 1150
RAIL_X0, RAIL_X1 = 130, W - 110
NANO_X, NANO_Y = 1150, 430          # Nano origin (left-top)
NANO_W_ = lib.NANO_W
KEY_X = 300                          # lemon column


# ── shared base: rails + Nano + 7-lemon keyboard ─────────────────────────────
def base(title, subtitle, board):
    s = Schematic(W, H, title=title, subtitle=subtitle)
    s.add_rail(Rail("5V", y=RAIL_5V_Y, x0=RAIL_X0, x1=RAIL_X1, color=C["v5"], label="+5 V"))
    s.add_rail(Rail("GND", y=RAIL_GND_Y, x0=RAIL_X0, x1=RAIL_X1, color=C["gnd"], label="GND"))

    s.add(lib.arduino_nano("U1", NANO_X, NANO_Y, board=board))
    s.connect("nano5v", C["v5"], P("U1", "5V"), R("5V"))
    s.connect("nanognd", C["gnd"], P("U1", "GND"), R("GND"))

    # hand-held 5 V clip (player)
    s.add(lib.clip_box("CLIP", 150, 150))
    s.connect("clip5v", C["v5"], P("CLIP", "out"), R("5V"))

    # 7 lemon keys → 220 Ω → A0..A6 (top row = Key7/A6, bottom = Key1/A0)
    key_ys = [312 + i * 94 for i in range(7)]
    order = [6, 5, 4, 3, 2, 1, 0]                    # analog index per row
    for row, ai in enumerate(order):
        ky = key_ys[row]
        s.add(lib.lemon_key(f"K{ai}", KEY_X, ky, ai + 1, f"A{ai}"))
        s.add(lib.resistor(f"RK{ai}", KEY_X + 150, ky, orient="H"))
        s.connect(f"kr{ai}", C["key"], P(f"K{ai}", "clip"), P(f"RK{ai}", "a"))
        s.connect(f"ka{ai}", C["key"], P(f"RK{ai}", "b"), P("U1", f"A{ai}"))

    s.decorations.append(deco.dashed_arrow(300, 242, 300, key_ys[0] - 36, C["key"],
                                           label="touch → body → lemon"))
    return s


LEGEND = dict(x=130, y=1210, w=W - 260, h=330)


# ── V4 / V4+ ─────────────────────────────────────────────────────────────────
def build_v4(plus=False):
    if plus:
        title = "Lemon Piano V4+ — original game + 2026 touch upgrade"
        sub = ("Same wiring as V4, plus MARGIN + (D10) / MARGIN − (D11) buttons. "
               "Auto-calibration is firmware — no extra wiring. Game unchanged.")
        fname = "wiring-v4-plus.png"
    else:
        title = "Lemon Piano V4 — original (relay water-pump + red/green LED)"
        sub = ("7 lemon touch keys · red/green LED · relay-driven water pump · "
               "game-select on D4 · restart · buzzer.")
        fname = "wiring-v4.png"

    s = base(title, sub, "ATmega328P · Nano / Uno")

    # feedback LEDs — anode faces the Nano (W), cathode drops to GND via 220 Ω
    lx = 1650
    s.add(lib.led("LEDR", lx, 560, (215, 45, 45), "RED LED", "D2 · wrong", anode="W"))
    s.add(lib.resistor("RR", lx, 700, orient="V"))
    s.connect("d2", C["led"], P("U1", "D2"), P("LEDR", "anode"))
    s.connect("rc", C["gnd"], P("LEDR", "cathode"), P("RR", "a"))
    s.connect("rg", C["gnd"], P("RR", "b"), R("GND"))

    lx2 = 1850
    s.add(lib.led("LEDG", lx2, 560, (45, 185, 75), "GREEN LED", "D3 · right", anode="W"))
    s.add(lib.resistor("RG", lx2, 700, orient="V"))
    s.connect("d3", C["led"], P("U1", "D3"), P("LEDG", "anode"))
    s.connect("gc", C["gnd"], P("LEDG", "cathode"), P("RG", "a"))
    s.connect("gg", C["gnd"], P("RG", "b"), R("GND"))

    # relay pair + water pump (far right)
    s.add(lib.relay_module("RLY", 2650, 560))
    s.add(lib.water_pump("PUMP", 2650, 780))
    s.connect("d5", C["relay"], P("U1", "D5"), P("RLY", "IN1"))
    s.connect("d6", C["relay"], P("U1", "D6"), P("RLY", "IN2"))
    s.connect("rlyv", C["v5"], P("RLY", "VCC"), R("5V"))
    s.connect("rlyg", C["gnd"], P("RLY", "GND"), R("GND"))
    s.connect("pump", C["relay"], P("RLY", "OUT"), P("PUMP", "in"))

    # game-select (D4) · buzzer (D8) · restart (D7)
    s.add(lib.spdt_switch("SEL", 2050, 900, "D4", com_facing="W"))
    s.connect("d4", C["ctrl"], P("U1", "D4"), P("SEL", "com"))
    s.connect("selv", C["v5"], P("SEL", "p5"), R("5V"))
    s.connect("selg", C["gnd"], P("SEL", "pg"), R("GND"))

    s.add(lib.buzzer("BUZ", 2250, 900))
    s.connect("d8", C["buzz"], P("U1", "D8"), P("BUZ", "sig"))
    s.connect("bg", C["gnd"], P("BUZ", "gnd"), R("GND"))

    _button(s, "RST", 2430, 900, "D7", "RESTART", "re-reads game", C["ctrl"], (70, 120, 200))

    if plus:
        _button(s, "MUP", 2620, 1010, "D10", "MARGIN +", "less sensitive", C["margin"], (220, 60, 150))
        _button(s, "MDN", 2820, 1010, "D11", "MARGIN −", "more sensitive", C["margin"], (220, 60, 150))

    _legend_v4(s, plus)
    return s, fname


def _button(s, cid, x, y, pin, label, sub, color, cap):
    """Active-HIGH button: pin → button → 5 V, plus a 10 kΩ pulldown to GND on the
    pin side (its own component, so the DRC proves it is connected). The Nano pin,
    the button's pin terminal and the pulldown top are ONE electrical node."""
    s.add(lib.push_button(cid, x, y, label, sub, cap=cap))
    s.add(lib.resistor(f"{cid}PD", x - 90, y + 30, orient="V", label="10k"))
    # one multi-terminal net for the pin-side node (router builds a clean tree)
    s.connect(f"{cid}sig", color, P("U1", pin), P(cid, "pin"), P(f"{cid}PD", "a"))
    s.connect(f"{cid}v5", C["v5"], P(cid, "v5"), R("5V"))
    s.connect(f"{cid}pg", C["gnd"], P(f"{cid}PD", "b"), R("GND"))


def _legend_v4(s, plus):
    entries = [
        (C["key"], "Lemon keys (7)", ["A0..A6 · 220 Ω each · 5 V through the body"]),
        (C["v5"], "+5 V / GND rails", ["Nano 5V/GND · relay VCC/GND · button pulldowns"]),
        (C["led"], "Feedback LEDs", ["RED (D2) = wrong · GREEN (D3) = right · 220 Ω"]),
        (C["relay"], "Relay + water pump", ["D5 (IN1) · D6 (IN2) → pump on a late miss"]),
        (C["ctrl"], "Controls", ["GAME SELECT (D4, SPDT) · RESTART (D7)"]),
        (C["buzz"], "Buzzer", ["D8 passive buzzer (key notes + tunes)"]),
    ]
    notes = [("Buttons are active-HIGH (to 5 V + 10k pulldown), matching the 2019 build.", C["muted"])]
    if plus:
        entries.append((C["margin"], "MARGIN +/− (D10/D11)",
                        ["nudge the touch margin live — see the 2026 upgrade"]))
        notes = [("MARGIN +/− tune touch sensitivity without a reflash; "
                  "auto-calibration runs at boot and every RESTART.", (180, 40, 120))]
    s.decorations.append(deco.legend(entries=entries, notes=notes, **LEGEND))


# ── V5 ───────────────────────────────────────────────────────────────────────
def build_v5():
    title = "Lemon Piano V5 — ten-LED progress bar (no pump)"
    sub = ("7 lemon keys · ten green LEDs (progress bar) · game-select on A7 · "
           "restart · buzzer. No relay, no pump, no red LED.")
    s = base(title, sub, "ATmega328P · Nano only (needs A6+A7)")

    # ten-LED progress bar
    pins = ["D2", "D3", "D4", "D5", "D6", "D9", "D10", "D11", "D12", "D13"]
    x0, dx, ybar = NANO_X + NANO_W_ + 120, 92, 980
    for i, pin in enumerate(pins):
        cx = x0 + i * dx
        cid = f"L{i}"
        s.add(lib.led(cid, cx, ybar, (45, 185, 75), str(i + 1), pin, anode="N", cathode="S"))
        s.add(lib.resistor(f"{cid}R", cx, ybar + 90, orient="V"))
        s.connect(f"a{i}", C["led"], P("U1", pin), P(cid, "anode"))
        s.connect(f"c{i}", C["gnd"], P(cid, "cathode"), P(f"{cid}R", "a"))
        s.connect(f"g{i}", C["gnd"], P(f"{cid}R", "b"), R("GND"))

    # game-select on A7 (analog), left of the Nano near A7
    s.add(lib.spdt_switch("SEL", 830, 250, "A7", com_facing="E", analog=True))
    s.connect("a7", C["ctrl"], P("SEL", "com"), P("U1", "A7"))
    s.connect("selv", C["v5"], P("SEL", "p5"), R("5V"))
    s.connect("selg", C["gnd"], P("SEL", "pg"), R("GND"))

    # restart + buzzer in the upper-right band
    _button(s, "RST", NANO_X + NANO_W_ + 420, 560, "D7", "RESTART", "re-reads game",
            C["ctrl"], (70, 120, 200))
    s.add(lib.buzzer("BUZ", NANO_X + NANO_W_ + 700, 560))
    s.connect("d8", C["buzz"], P("U1", "D8"), P("BUZ", "sig"))
    s.connect("bg", C["gnd"], P("BUZ", "gnd"), R("GND"))

    entries = [
        (C["key"], "Lemon keys (7)", ["A0..A6 · 220 Ω each · 5 V through the body"]),
        (C["v5"], "+5 V / GND rails", ["Nano 5V/GND · LED cathodes · button pulldown"]),
        (C["led"], "Progress bar (10 LEDs)",
         ["D2,3,4,5,6,9,10,11,12,13 · 220 Ω each", "1 LED per correct note · all 10 = win"]),
        (C["ctrl"], "Controls", ["GAME SELECT on A7 (SPDT, analog-in) · RESTART (D7)"]),
        (C["buzz"], "Buzzer", ["D8 passive buzzer (key notes + victory tunes)"]),
    ]
    notes = [("Every I/O line is used: A0–A7 + D2–D13. A7 is analog-in only — drive it "
              "with an SPDT to 5 V / GND. A classic Uno lacks A6/A7.", C["muted"])]
    s.decorations.append(deco.legend(entries=entries, notes=notes, **LEGEND))
    return s, "wiring-v5.png"


NANO_W_ = lib.NANO_W


if __name__ == "__main__":
    for builder in (lambda: build_v4(False), lambda: build_v4(True), build_v5):
        s, fname = builder()
        build(s)
        print("Saved:", save(s, str(OUT / fname)))
