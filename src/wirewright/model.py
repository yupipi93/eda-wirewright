"""Declarative schematic model — the 'contract'. You describe WHAT is connected
to what (components, ports, nets); the engine figures out HOW to draw it without
overlaps. No PIL, no routing here — pure description.

Coordinates are absolute pixels (a component factory in library.py places its
body + ports at a given anchor). Placement stays declarative on purpose: for a
known circuit a human-guided left→right flow beats auto-placement, and the hard
part (clean wiring) is fully automatic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .geometry import BBox

# A port faces one of the four cardinal directions; its escape stub leaves that way.
FACING = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}


@dataclass
class Port:
    name: str
    x: float
    y: float
    facing: str            # 'N' | 'S' | 'E' | 'W' — direction the wire leaves the pin
    draw_stub: bool = True  # engine draws the short perpendicular pin stub


@dataclass
class Component:
    id: str
    body: BBox                       # obstacle box (wires route around this)
    ports: dict                      # name -> Port (absolute coords)
    draw: Callable                   # draw(painter) -> renders body + fixed labels
    clearance: float = 14.0          # keep-out halo around the body for routing
    is_obstacle: bool = True
    label_boxes: list = field(default_factory=list)  # extra text AABBs for DRC

    def port(self, name) -> Port:
        return self.ports[name]


@dataclass
class Rail:
    name: str
    y: float
    x0: float
    x1: float
    color: tuple
    label: str = ""
    label_x: Optional[float] = None   # where to print the rail name (defaults to x1+12)
    width: int = 7


# ── net terminals ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PortRef:
    comp: str
    port: str


@dataclass(frozen=True)
class RailRef:
    rail: str


@dataclass(frozen=True)
class PointRef:
    x: float
    y: float


@dataclass
class Net:
    name: str
    color: tuple
    nodes: list                      # list of PortRef | RailRef | PointRef  (>=2)
    width: int = 5
    style: str = "wire"              # 'wire' (routed) | 'label' (named-net stubs)
    priority: int = 0                # lower routes first; auto-set to span if 0


@dataclass
class Schematic:
    w: int
    h: int
    title: str = ""
    subtitle: str = ""
    bg: tuple = (250, 250, 248)
    components: dict = field(default_factory=dict)   # id -> Component
    rails: dict = field(default_factory=dict)        # name -> Rail
    nets: list = field(default_factory=list)
    decorations: list = field(default_factory=list)  # extra draw(painter) callables (legend, notes)
    legend: Optional[dict] = None

    def add(self, comp: Component) -> Component:
        self.components[comp.id] = comp
        return comp

    def add_rail(self, rail: Rail) -> Rail:
        self.rails[rail.name] = rail
        return rail

    def connect(self, name, color, *nodes, width=5, style="wire", priority=0):
        self.nets.append(Net(name, color, list(nodes), width=width, style=style, priority=priority))

    def resolve(self, node):
        """Return absolute (x, y, facing) for a terminal node. Rails resolve to
        their y with x=None (any-x target, handled by the router)."""
        if isinstance(node, PortRef):
            p = self.components[node.comp].port(node.port)
            return (p.x, p.y, p.facing)
        if isinstance(node, PointRef):
            return (node.x, node.y, None)
        if isinstance(node, RailRef):
            r = self.rails[node.rail]
            return (None, r.y, None)
        raise TypeError(node)
