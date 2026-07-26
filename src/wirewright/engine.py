"""Orchestration: turn a declarative Schematic into a validated PNG.

    place (declared)  ->  stamp obstacles  ->  route (ordered, sequential)
      ->  junction dots  ->  DRC validate  ->  render

Routing order is shortest-span-first (most constrained nets get first pick of
the free space), matching the research's net-ordering advice."""
from __future__ import annotations

from . import validator as drc
from .config import Config
from .grid import RoutingGrid
from .model import PointRef, PortRef
from .painter import Painter
from .router import route_net


class DRCError(AssertionError):
    """Raised when a diagram violates a hard design rule. `.violations` holds the
    machine-readable list so callers (CLI, MCP) can report them structurally."""
    def __init__(self, violations):
        self.violations = violations
        lines = "\n".join(f"  - [{v.kind}] {v.msg}" for v in violations[:40])
        super().__init__(f"DRC failed with {len(violations)} violation(s):\n{lines}")


class BuildResult:
    def __init__(self, grid, routed, soft):
        self.grid = grid
        self.routed = routed
        self.soft = soft         # spacing warnings (non-fatal unless strict)

    @property
    def net_count(self):
        return len(self.routed)


def _net_span(schematic, net):
    pts = []
    for n in net.nodes:
        if isinstance(n, (PortRef, PointRef)):
            x, y, _ = schematic.resolve(n)
            pts.append((x, y))
    if len(pts) < 2:
        return 0
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (max(xs) - min(xs)) + (max(ys) - min(ys))


def _junction_dots(res):
    """A tree cell with >=3 net neighbours is a real T/4-way tap -> dot."""
    cells = res.tree_cells
    dots = []
    for (cx, cy) in cells:
        deg = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (cx + dx, cy + dy) in cells:
                deg += 1
        if deg >= 3:
            dots.append((cx, cy))
    return dots


def build(schematic, cfg=None, debug=False, verbose=True):
    """Place → route → DRC → render. Raises DRCError on any hard violation, so a
    broken diagram can never be saved. Returns a BuildResult."""
    cfg = cfg or Config()
    grid = RoutingGrid(schematic.w, schematic.h, pitch=cfg.router.pitch)

    # obstacles: component bodies + clearance, and external text as soft cost
    for comp in schematic.components.values():
        if comp.is_obstacle:
            grid.block_box(comp.body, clearance=comp.clearance,
                           skirt_cost=cfg.router.body_skirt_cost)
        for lb in comp.label_boxes:
            grid.add_soft_box(lb, cost=cfg.router.label_soft_cost)

    # route nets, shortest-span first
    nets = sorted(schematic.nets,
                  key=lambda n: (n.priority or _net_span(schematic, n)))
    routed = []
    for net in nets:
        if net.style == "label":
            continue   # (label-style nets handled in render as named stubs)
        res = route_net(schematic, grid, net, cfg)
        routed.append((net, res))

    # DRC
    hard, soft = drc.check(schematic, routed, cfg)
    if hard:
        raise DRCError(hard)
    if verbose:
        print(f"  DRC OK — {len(routed)} nets routed, "
              f"{len(soft)} spacing warning(s), 0 hard violations")

    _render(schematic, routed, grid, debug=debug, soft=soft)
    return BuildResult(grid, routed, soft)


def _render(schematic, routed, grid, debug=False, soft=None):
    p = Painter(schematic.w, schematic.h, bg=schematic.bg)
    if schematic.title:
        p.text((schematic.w // 2, 26), schematic.title, font="title", anchor="mt")
    if schematic.subtitle:
        p.text((schematic.w // 2, 78), schematic.subtitle, font="sub", anchor="mt")

    # rails
    for rail in schematic.rails.values():
        p.line([(rail.x0, rail.y), (rail.x1, rail.y)], fill=rail.color, width=rail.width)
        if rail.label:
            lx = rail.label_x if rail.label_x is not None else rail.x1 + 12
            p.text((lx, rail.y), rail.label, font="leg", fill=rail.color, anchor="lm")

    # wires (under component bodies so pins look plugged-in)
    for net, res in routed:
        for pl in res.polylines:
            if len(pl) >= 2:
                p.line(pl, fill=net.color, width=net.width)

    # junction dots + rail hits
    for net, res in routed:
        for (cx, cy) in _junction_dots(res):
            wx, wy = grid.to_world(cx, cy)
            p.dot(wx, wy, max(4, net.width // 2 + 2), net.color)
        for (wx, wy) in res.rail_hits:
            p.dot(wx, wy, 6, (35, 35, 40))

    # component bodies + fixed labels on top
    for comp in schematic.components.values():
        comp.draw(p)

    # decorations (legend, notes, dashed annotations)
    for deco in schematic.decorations:
        deco(p)

    if debug and soft:
        for v in soft:
            x, y = v.where
            p.circle(x, y, 12, outline=(255, 0, 0), width=3)

    schematic._painter = p
    return p


def save(schematic, path):
    schematic._painter.save(path)
    return path
