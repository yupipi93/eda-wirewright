# `schematic` — a tiny declarative schematic/wiring-diagram engine

Describe **what connects to what** (components, ports, nets); the engine works out
**how to draw it** — orthogonal wires that never cross a component body, never run
on top of each other, never leave a pin dangling, and keep their distance. Every
diagram is **DRC-validated before it is saved**, so a broken image can't slip out.

Built to replace hand-placed coordinates (where wires overlapped bodies, crossed
confusingly, ran too close, and left resistors visually unconnected) with a real
router + validator. It is generic: add components and nets and it composes any
schematic.

## Why it looks clean (the two levers that matter)

1. **Grid A\* maze router with a large bend penalty.** Wires are shortest
   orthogonal paths on a routing grid, but turning is ~14× the cost of going
   straight — so wires run in long straight lines with few corners (the
   CAD-drawn look). Component bodies (plus a clearance halo) are hard obstacles,
   so a wire *cannot* cross one. Each pin gets a mandatory perpendicular **escape
   stub** so wires always leave pins at right angles.
2. **A light proximity penalty + sequential routing.** Each net is committed to
   the grid before the next routes, leaving a small crowding halo. Later wires
   prefer to shift one track over rather than sit on top of a neighbour — but the
   penalty is deliberately small, so they *cross* cleanly instead of taking long
   detours (crossings between different nets are fine and get no junction dot).

External text (labels) is handed to the router as a **soft** obstacle, so wires
route around labels where they can.

## The pipeline (`engine.build`)

```
stamp obstacles (bodies + clearance, labels as soft cost)
  → route nets shortest-span-first (grid A*, multi-terminal Steiner-ish trees)
  → junction dots (a tree cell with ≥3 same-net neighbours = a real tap)
  → DRC validate  → render to PNG
```

## DRC (`validator.py`) — the "no faults" guarantee

Raises on any of these (the exact faults this engine was built to kill):

| check | rule |
|---|---|
| `wire-over-component` | no wire segment passes through a component body |
| `coincident-wires`    | no two different nets drawn on top of each other |
| `unconnected-pin`     | every port named in a net has a wire endpoint on it |
| `wires-too-close`     | parallel different-net wires stay ≥ `MIN_WIRE_SPACING` apart |

## Writing a diagram (the "contract")

```python
from schematic import Schematic, lib, P, R, Rail, build, save, C, deco

s = Schematic(3400, 1580, title="…", subtitle="…")
s.add_rail(Rail("5V",  y=360,  x0=130, x1=3290, color=C["v5"],  label="+5 V"))
s.add_rail(Rail("GND", y=1150, x0=130, x1=3290, color=C["gnd"], label="GND"))

s.add(lib.arduino_nano("U1", 1150, 430))
s.add(lib.led("LEDR", 1650, 560, (215,45,45), "RED LED", "D2", anode="W"))
s.add(lib.resistor("RR", 1650, 700, orient="V"))

s.connect("d2", C["led"], P("U1","D2"), P("LEDR","anode"))          # pin → pin
s.connect("rc", C["gnd"], P("LEDR","cathode"), P("RR","a"))
s.connect("rg", C["gnd"], P("RR","b"), R("GND"))                    # pin → rail
s.connect("pwr", C["v5"], P("U1","5V"), R("5V"))

build(s, pitch=10)        # routes + DRC (raises on any violation)
save(s, "out.png")
```

- `P(comp, port)` = a component port · `R(rail)` = the +5 V / GND bus · a net with
  **3+ terminals** (e.g. a Nano pin + a button + its pulldown that are one
  electrical node) is routed as one clean tree.
- Placement is **declarative** (you choose x/y): for a known circuit a
  human-guided left→right flow beats auto-placement, and the hard part — clean
  wiring — is automatic. (Force-directed auto-placement is a possible future
  add; the model already carries everything it would need.)

## Files

| file | role |
|---|---|
| `model.py` | `Schematic`, `Component`, `Port`, `Rail`, `Net`, terminals (`PortRef`/`RailRef`/`PointRef`) |
| `library.py` | component factories (Nano, LED, resistor, button, buzzer, SPDT, relay, pump, lemon key, clip) + `LabelBag` |
| `grid.py` | routing grid: obstacles, clearance skirt, crowding halo, soft label cost |
| `router.py` | grid A* (state = cell + incoming direction), multi-terminal trees, rail targets, escape stubs |
| `validator.py` | geometric DRC (see table above) |
| `geometry.py` | pure segment/box tests (segment-crosses-box, collinear overlap, parallel gap…) |
| `painter.py` | thin PIL wrapper + fonts + text metrics |
| `decorations.py` | legend, notes, dashed annotations |
| `engine.py` | orchestration + junction dots + render |

## Tuning knobs

- `router.BEND_PENALTY` — higher = straighter, fewer corners.
- `grid.commit_wire(halo_cost, self_cost)` — higher = wires spread more / avoid
  crossings more (too high → ugly detours; keep small).
- `engine.build(pitch=…)` — grid resolution (smaller = finer routes, slower).
- `validator.MIN_WIRE_SPACING` — the spacing DRC threshold.

## Design sources

Grid maze routing (Lee/A\*), bend/proximity cost, channel/track spacing,
net-ordering, junction-dot rules and label placement follow standard EDA
practice (KiCad/Altium conventions; Wybrow et al. *Orthogonal Connector Routing*,
GD 2009; VLSI physical-design routing literature).
