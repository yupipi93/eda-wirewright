"""Grid A* maze router — the heart of the engine.

Per net it builds a Steiner-ish tree: seed with the first terminal, then A* each
remaining terminal to the nearest cell ALREADY in the net's tree. Later terminals
can join mid-wire, which is what creates clean T-taps. Each net is committed to
the grid before the next routes (sequential / rip-up-free), so wires see each
other as soft obstacles and spread out.

The two levers the research flagged as decisive:
  * a LARGE bend penalty  -> long straight runs, few corners (the CAD look)
  * a proximity penalty    -> wires keep clear of bodies and of each other
State is (cell_x, cell_y, incoming_dir) so bends can be detected and penalised."""
from __future__ import annotations

import heapq

from .model import FACING, RailRef

# E, W, S, N
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
FACE_TO_DIR = {"E": 0, "W": 1, "S": 2, "N": 3}


class RouteResult:
    def __init__(self):
        self.polylines = []      # list of [(x,y), ...] world-space wire runs
        self.rail_hits = []      # (x, y) where a wire meets a rail -> junction dot
        self.tree_cells = set()  # every grid cell the net occupies


def _cells_bbox(cells):
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
    return min(xs), min(ys), max(xs), max(ys)


def _astar(grid, sources, goals, src_dir_of, cfg):
    """Shortest orthogonal path from any source cell to any goal cell.
    sources/goals: sets of (cx,cy). src_dir_of: {cell: dir_index or -1}.
    Returns list of cells [source..goal] or None."""
    bend = cfg.router.bend_penalty
    prox = cfg.router.proximity_k
    goals = set(goals)
    if not goals or not sources:
        return None
    gx0, gy0, gx1, gy1 = _cells_bbox(goals)

    def h(x, y):
        dx = 0 if gx0 <= x <= gx1 else min(abs(x - gx0), abs(x - gx1))
        dy = 0 if gy0 <= y <= gy1 else min(abs(y - gy0), abs(y - gy1))
        return dx + dy

    pq = []
    best = {}
    came = {}
    for (cx, cy) in sources:
        d0 = src_dir_of.get((cx, cy), -1)
        st = (cx, cy, d0)
        best[st] = 0.0
        heapq.heappush(pq, (h(cx, cy), 0.0, cx, cy, d0))
    while pq:
        f, g, x, y, d = heapq.heappop(pq)
        st = (x, y, d)
        if best.get(st, 1e18) < g:
            continue
        if (x, y) in goals:
            # backtrace
            path = [(x, y)]
            cur = st
            while cur in came:
                cur = came[cur]
                path.append((cur[0], cur[1]))
            path.reverse()
            return path
        for i, (dx, dy) in enumerate(DIRS):
            nx, ny = x + dx, y + dy
            if not grid.inb(nx, ny):
                continue
            # goal/tree cells are allowed even if 'used' (same net merge);
            # otherwise obstacles are hard-blocked.
            if grid.is_blocked(nx, ny) and (nx, ny) not in goals:
                continue
            step = 1.0
            if d != -1 and i != d:
                step += bend
            step += prox * grid.crowd_at(nx, ny)
            ng = g + step
            nst = (nx, ny, i)
            if ng < best.get(nst, 1e18):
                best[nst] = ng
                came[nst] = st
                heapq.heappush(pq, (ng + h(nx, ny), ng, nx, ny, i))
    return None


def _simplify(cells, grid):
    """Collapse a run of cells into polyline vertices at every bend, in world
    coords."""
    if not cells:
        return []
    pts = [grid.to_world(*cells[0])]
    for i in range(1, len(cells) - 1):
        ax, ay = cells[i - 1]; bx, by = cells[i]; cx, cy = cells[i + 1]
        if (bx - ax, by - ay) != (cx - bx, cy - by):   # direction changed -> vertex
            pts.append(grid.to_world(bx, by))
    pts.append(grid.to_world(*cells[-1]))
    return pts


def _node_anchor(schematic, grid, node, cfg):
    """Return (source_cells, dir_of, stub_polyline) for a terminal.
    - port/point: one stub-end cell + the drawn pin->stub segment
    - rail:       all free cells along the rail (no stub)"""
    if isinstance(node, RailRef):
        rail = schematic.rails[node.rail]
        cells = []
        cy = grid.to_cell(rail.x0, rail.y)[1]
        cx0 = grid.to_cell(rail.x0, rail.y)[0]
        cx1 = grid.to_cell(rail.x1, rail.y)[0]
        for cx in range(cx0, cx1 + 1):
            if grid.inb(cx, cy) and not grid.blocked[grid._i(cx, cy)]:
                cells.append((cx, cy))
        return set(cells), {}, None, ("rail", rail)

    x, y, facing = schematic.resolve(node)
    if facing is None:
        facing = "E"
    dx, dy = FACING[facing]
    stub_px = cfg.router.stub_px
    ex, ey = x + dx * stub_px, y + dy * stub_px
    grid.carve_line(x, y, ex, ey)               # guarantee the pin can escape
    grid.carve(ex, ey, radius_cells=0)
    cell = grid.to_cell(ex, ey)
    dir_of = {cell: FACE_TO_DIR[facing]}
    stub = [(x, y), (ex, ey)]
    return {cell}, dir_of, stub, ("pin", (x, y))


def route_net(schematic, grid, net, cfg):
    res = RouteResult()
    anchors = [_node_anchor(schematic, grid, n, cfg) for n in net.nodes]

    # seed the tree with the first non-rail anchor if possible (a fixed point is
    # a better seed than a whole rail line)
    order = sorted(range(len(anchors)), key=lambda k: 0 if anchors[k][3][0] == "pin" else 1)
    first = order[0]
    tree = set(anchors[first][0])
    if anchors[first][2]:
        res.polylines.append(anchors[first][2])
        # include stub cells in the tree so branches can tap the stub
        _add_seg_cells(grid, anchors[first][2], tree)

    for k in order[1:]:
        sources, dir_of, stub, kind = anchors[k]
        path = _astar(grid, sources, tree, dir_of, cfg)
        if path is None:
            raise RuntimeError(f"net {net.name!r}: could not route terminal {kind}")
        res.polylines.append(_simplify(path, grid))
        for c in path:
            tree.add(c)
        if stub:
            res.polylines.append(stub)
            _add_seg_cells(grid, stub, tree)
        if kind[0] == "rail":
            res.rail_hits.append(grid.to_world(*path[0]))

    res.tree_cells = tree
    grid.commit_wire(tree, halo=cfg.router.wire_halo,
                     halo_cost=cfg.router.wire_halo_cost,
                     self_cost=cfg.router.wire_self_cost)
    return res


def _add_seg_cells(grid, polyline, cellset):
    for i in range(len(polyline) - 1):
        x0, y0 = polyline[i]; x1, y1 = polyline[i + 1]
        c0 = grid.to_cell(x0, y0); c1 = grid.to_cell(x1, y1)
        if c0[0] == c1[0]:
            for cy in range(min(c0[1], c1[1]), max(c0[1], c1[1]) + 1):
                cellset.add((c0[0], cy))
        else:
            for cx in range(min(c0[0], c1[0]), max(c0[0], c1[0]) + 1):
                cellset.add((cx, c0[1]))
