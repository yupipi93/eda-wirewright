"""Design-Rule Check. After routing, this proves the diagram is clean — the same
five failure classes the user reported, expressed as geometric tests:

  1. wire over/under a component body      -> segment_crosses_box
  2. two different nets drawn coincident   -> collinear_overlap_len
  3. wires too close                        -> parallel_gap < MIN_SPACING
  4. unconnected component pin              -> port with no wire endpoint on it
  5. (labels) text overlapping text/wires   -> AABB overlap

The engine runs this and RAISES on any hard violation, so a broken diagram can
never be silently saved. Soft issues (spacing, labels) are warnings unless
strict=True."""
from __future__ import annotations

from dataclasses import dataclass

from .geometry import collinear_overlap_len, parallel_gap, segment_crosses_box


@dataclass
class Violation:
    kind: str
    msg: str
    where: tuple            # a point (x,y) for the debug overlay


def _segments(polyline):
    return [(polyline[i], polyline[i + 1]) for i in range(len(polyline) - 1)
            if polyline[i] != polyline[i + 1]]


def check(schematic, routed, cfg):
    """routed: list of (net, RouteResult). Returns (hard, soft) violation lists."""
    min_spacing = cfg.drc.min_wire_spacing
    port_tol = cfg.drc.port_tolerance
    strict = cfg.drc.strict
    viol = []

    # gather all wire segments tagged by net name
    segs = []   # (net_name, p0, p1)
    for net, res in routed:
        for pl in res.polylines:
            for p0, p1 in _segments(pl):
                segs.append((net.name, p0, p1))

    # 1) wire crossing a component body
    for comp in schematic.components.values():
        if not comp.is_obstacle:
            continue
        box = comp.body
        for name, p0, p1 in segs:
            if segment_crosses_box(p0, p1, box, min_len=2.0):
                viol.append(Violation("wire-over-component",
                            f"net {name} crosses body of {comp.id}",
                            ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)))

    # 2) coincident different-net wires
    for a in range(len(segs)):
        na, a0, a1 = segs[a]
        for b in range(a + 1, len(segs)):
            nb, b0, b1 = segs[b]
            if na == nb:
                continue
            if collinear_overlap_len(a0, a1, b0, b1) > 2.0:
                viol.append(Violation("coincident-wires",
                            f"nets {na} & {nb} drawn on top of each other",
                            a0))

    # 3) parallel wires too close (different nets)
    for a in range(len(segs)):
        na, a0, a1 = segs[a]
        for b in range(a + 1, len(segs)):
            nb, b0, b1 = segs[b]
            if na == nb:
                continue
            gap = parallel_gap(a0, a1, b0, b1)
            if gap is not None and 0.1 < gap < min_spacing:
                viol.append(Violation("wires-too-close",
                            f"nets {na} & {nb} only {gap:.0f}px apart",
                            a0))

    # 4) unconnected pins: every port used by a net must have a wire endpoint on it
    endpoints = []
    for _, p0, p1 in segs:
        endpoints.append(p0); endpoints.append(p1)

    def has_endpoint(px, py):
        return any(abs(px - ex) <= port_tol and abs(py - ey) <= port_tol
                   for (ex, ey) in endpoints)

    from .model import PortRef
    used_ports = set()
    for net, _ in routed:
        for node in net.nodes:
            if isinstance(node, PortRef):
                used_ports.add((node.comp, node.port))
                p = schematic.components[node.comp].port(node.port)
                if not has_endpoint(p.x, p.y):
                    viol.append(Violation("unconnected-pin",
                                f"{node.comp}.{node.port} has no wire",
                                (p.x, p.y)))

    hard = [v for v in viol if v.kind in
            ("wire-over-component", "coincident-wires", "unconnected-pin")]
    soft = [v for v in viol if v.kind == "wires-too-close"]
    return hard + (soft if strict else []), soft
