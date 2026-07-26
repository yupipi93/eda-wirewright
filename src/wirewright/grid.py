"""The routing grid. Everything the router needs to know about space lives here:
which cells are blocked (component bodies + clearance), and how 'crowded' each
free cell is (near an obstacle or an already-routed wire). Snapping the whole
diagram to this grid is what makes wires look CAD-drawn instead of hand-placed.

Flat arrays keyed by y*nx+x for speed in pure Python."""
from __future__ import annotations

from array import array

from .geometry import BBox


class RoutingGrid:
    def __init__(self, w, h, pitch=10):
        self.pitch = pitch
        self.nx = w // pitch + 1
        self.ny = h // pitch + 1
        n = self.nx * self.ny
        self.blocked = bytearray(n)         # 1 = obstacle, cannot route here
        self.crowd = array("f", [0.0]) * n  # extra soft cost (proximity to stuff)
        self.used = bytearray(n)            # 1 = a committed wire passes here

    # ---- coordinate mapping ----
    def to_cell(self, x, y):
        return (int(round(x / self.pitch)), int(round(y / self.pitch)))

    def to_world(self, cx, cy):
        return (cx * self.pitch, cy * self.pitch)

    def inb(self, cx, cy):
        return 0 <= cx < self.nx and 0 <= cy < self.ny

    def _i(self, cx, cy):
        return cy * self.nx + cx

    # ---- obstacles ----
    def block_box(self, box: BBox, clearance=0.0, skirt_cost=2.5):
        b = box.inflate(clearance)
        x0, y0 = self.to_cell(b.x0, b.y0)
        x1, y1 = self.to_cell(b.x1, b.y1)
        for cy in range(max(0, y0), min(self.ny, y1 + 1)):
            row = cy * self.nx
            for cx in range(max(0, x0), min(self.nx, x1 + 1)):
                self.blocked[row + cx] = 1
        # a light crowding skirt just outside the clearance, so wires prefer to
        # keep a little air around bodies even where they're technically allowed
        self._skirt(box.inflate(clearance), extra=2, cost=skirt_cost)

    def _skirt(self, box: BBox, extra, cost):
        x0, y0 = self.to_cell(box.x0, box.y0)
        x1, y1 = self.to_cell(box.x1, box.y1)
        for cy in range(max(0, y0 - extra), min(self.ny, y1 + 1 + extra)):
            for cx in range(max(0, x0 - extra), min(self.nx, x1 + 1 + extra)):
                i = self._i(cx, cy)
                if not self.blocked[i]:
                    self.crowd[i] += cost

    def add_soft_box(self, box: BBox, cost):
        """Mark a region (e.g. a text label) as expensive-but-not-blocked, so
        wires route around it when they can but ports underneath still escape."""
        x0, y0 = self.to_cell(box.x0, box.y0)
        x1, y1 = self.to_cell(box.x1, box.y1)
        for cy in range(max(0, y0), min(self.ny, y1 + 1)):
            for cx in range(max(0, x0), min(self.nx, x1 + 1)):
                i = self._i(cx, cy)
                if not self.blocked[i]:
                    self.crowd[i] += cost

    def carve(self, x, y, radius_cells=0):
        """Force a small area free (for pin cells + escape stubs that would
        otherwise fall inside a body's clearance)."""
        cx, cy = self.to_cell(x, y)
        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                if self.inb(cx + dx, cy + dy):
                    self.blocked[self._i(cx + dx, cy + dy)] = 0

    def carve_line(self, x0, y0, x1, y1):
        """Free every cell along an orthogonal stub so a pin can always escape."""
        cx0, cy0 = self.to_cell(x0, y0)
        cx1, cy1 = self.to_cell(x1, y1)
        if cx0 == cx1:
            for cy in range(min(cy0, cy1), max(cy0, cy1) + 1):
                if self.inb(cx0, cy):
                    self.blocked[self._i(cx0, cy)] = 0
        else:
            for cx in range(min(cx0, cx1), max(cx0, cx1) + 1):
                if self.inb(cx, cy0):
                    self.blocked[self._i(cx, cy0)] = 0

    # ---- wire commit (sequential routing) ----
    def commit_wire(self, cells, halo=1, halo_cost=3.0, self_cost=6.0):
        """Mark a routed net's cells as used, and add a light crowding halo so
        later nets prefer to keep a track's distance. Costs are deliberately
        SMALL: a wire should shift over one track or cross cleanly, never take a
        long detour to avoid another wire (crossings between nets are fine)."""
        for (cx, cy) in cells:
            if self.inb(cx, cy):
                i = self._i(cx, cy)
                self.used[i] = 1
                self.crowd[i] += self_cost
        for (cx, cy) in cells:
            for dy in range(-halo, halo + 1):
                for dx in range(-halo, halo + 1):
                    if (dx or dy) and self.inb(cx + dx, cy + dy):
                        self.crowd[self._i(cx + dx, cy + dy)] += halo_cost

    # ---- queries ----
    def is_blocked(self, cx, cy):
        return not self.inb(cx, cy) or self.blocked[self._i(cx, cy)]

    def crowd_at(self, cx, cy):
        return self.crowd[self._i(cx, cy)] if self.inb(cx, cy) else 0.0

    def is_used(self, cx, cy):
        return self.inb(cx, cy) and self.used[self._i(cx, cy)]
