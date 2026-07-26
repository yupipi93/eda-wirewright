"""Pure-geometry helpers — no PIL, no state. The validator and router lean on
these; keeping them dependency-free makes them trivially unit-testable.

Everything works in integer-ish pixel space (floats accepted, compared with a
small epsilon where needed)."""
from __future__ import annotations

import math
from dataclasses import dataclass

EPS = 1e-6


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self):
        # normalise so x0<=x1, y0<=y1 (frozen: use object.__setattr__)
        if self.x0 > self.x1:
            object.__setattr__(self, "x0", self.x1)
            object.__setattr__(self, "x1", self.x0)
        if self.y0 > self.y1:
            object.__setattr__(self, "y0", self.y1)
            object.__setattr__(self, "y1", self.y0)

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    def inflate(self, m: float) -> "BBox":
        return BBox(self.x0 - m, self.y0 - m, self.x1 + m, self.y1 + m)

    def contains_point(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def overlaps(self, other: "BBox") -> bool:
        return not (self.x1 <= other.x0 or other.x1 <= self.x0
                    or self.y1 <= other.y0 or other.y1 <= self.y0)


def _seg_rect_overlap_len(p0, p1, box: BBox) -> float:
    """Length of an ORTHOGONAL segment p0-p1 that lies strictly inside `box`.
    Returns 0 if the segment only touches the border. Only orthogonal segments
    occur in these schematics, which makes this exact and cheap."""
    (x0, y0), (x1, y1) = p0, p1
    if abs(x0 - x1) < EPS:                      # vertical
        x = x0
        if not (box.x0 - EPS < x < box.x1 + EPS):
            return 0.0
        if box.x0 + EPS >= x or x >= box.x1 - EPS:
            return 0.0                          # exactly on a vertical edge → touch, not cross
        lo, hi = sorted((y0, y1))
        a, b = max(lo, box.y0), min(hi, box.y1)
        return max(0.0, b - a)
    if abs(y0 - y1) < EPS:                      # horizontal
        y = y0
        if not (box.y0 - EPS < y < box.y1 + EPS):
            return 0.0
        if box.y0 + EPS >= y or y >= box.y1 - EPS:
            return 0.0
        lo, hi = sorted((x0, x1))
        a, b = max(lo, box.x0), min(hi, box.x1)
        return max(0.0, b - a)
    # non-orthogonal fallback: sample
    n = 24
    inside = 0
    for i in range(n + 1):
        t = i / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if box.x0 + EPS < x < box.x1 - EPS and box.y0 + EPS < y < box.y1 - EPS:
            inside += 1
    return (inside / (n + 1)) * math.hypot(x1 - x0, y1 - y0)


def segment_crosses_box(p0, p1, box: BBox, min_len: float = 1.0) -> bool:
    """True if the segment passes THROUGH the interior of box for at least
    min_len px (touching an edge, e.g. a wire meeting a component border at a
    port, does not count)."""
    return _seg_rect_overlap_len(p0, p1, box) >= min_len


def _on_segment(p, a, b) -> bool:
    (px, py), (ax, ay), (bx, by) = p, a, b
    return (min(ax, bx) - EPS <= px <= max(ax, bx) + EPS
            and min(ay, by) - EPS <= py <= max(ay, by) + EPS)


def collinear_overlap_len(a0, a1, b0, b1) -> float:
    """If two ORTHOGONAL segments are collinear and overlap, return the overlap
    length; else 0. This is the 'two wires drawn on top of each other' test."""
    ax0, ay0 = a0; ax1, ay1 = a1
    bx0, by0 = b0; bx1, by1 = b1
    a_vert = abs(ax0 - ax1) < EPS
    b_vert = abs(bx0 - bx1) < EPS
    a_horiz = abs(ay0 - ay1) < EPS
    b_horiz = abs(by0 - by1) < EPS
    if a_vert and b_vert and abs(ax0 - bx0) < EPS:
        lo = max(min(ay0, ay1), min(by0, by1))
        hi = min(max(ay0, ay1), max(by0, by1))
        return max(0.0, hi - lo)
    if a_horiz and b_horiz and abs(ay0 - by0) < EPS:
        lo = max(min(ax0, ax1), min(bx0, bx1))
        hi = min(max(ax0, ax1), max(bx0, bx1))
        return max(0.0, hi - lo)
    return 0.0


def segments_cross(a0, a1, b0, b1):
    """Return the crossing point of two ORTHOGONAL segments (one vertical, one
    horizontal) if they intersect at a single interior/endpoint point, else None.
    Collinear overlaps return None (handled by collinear_overlap_len)."""
    ax0, ay0 = a0; ax1, ay1 = a1
    bx0, by0 = b0; bx1, by1 = b1
    a_vert = abs(ax0 - ax1) < EPS
    b_vert = abs(bx0 - bx1) < EPS
    if a_vert and not b_vert:
        x = ax0
        y = by0
        if (min(ay0, ay1) - EPS <= y <= max(ay0, ay1) + EPS
                and min(bx0, bx1) - EPS <= x <= max(bx0, bx1) + EPS):
            return (x, y)
        return None
    if b_vert and not a_vert:
        return segments_cross(b0, b1, a0, a1)
    return None


def point_to_segment_dist(p, a, b) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if abs(dx) < EPS and abs(dy) < EPS:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def parallel_gap(a0, a1, b0, b1):
    """For two parallel ORTHOGONAL segments that share an overlapping projection,
    return their perpendicular gap; else None. Used to flag 'wires too close'."""
    ax0, ay0 = a0; ax1, ay1 = a1
    bx0, by0 = b0; bx1, by1 = b1
    a_vert = abs(ax0 - ax1) < EPS
    b_vert = abs(bx0 - bx1) < EPS
    a_horiz = abs(ay0 - ay1) < EPS
    b_horiz = abs(by0 - by1) < EPS
    if a_vert and b_vert:
        lo = max(min(ay0, ay1), min(by0, by1))
        hi = min(max(ay0, ay1), max(by0, by1))
        if hi - lo <= EPS:
            return None
        return abs(ax0 - bx0)
    if a_horiz and b_horiz:
        lo = max(min(ax0, ax1), min(bx0, bx1))
        hi = min(max(ax0, ax1), max(bx0, bx1))
        if hi - lo <= EPS:
            return None
        return abs(ay0 - by0)
    return None
