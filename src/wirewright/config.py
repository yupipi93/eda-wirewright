"""All tunables in one place. Pass a Config to `build()`, or override individual
fields from the CLI / JSON `config` block. Sensible defaults give clean diagrams
out of the box; the knobs exist for dense or unusual layouts."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class RouterConfig:
    pitch: int = 10                    # routing-grid resolution in px (smaller = finer, slower)
    bend_penalty: float = 14.0         # cost of a corner vs a straight step (higher = straighter)
    proximity_k: float = 1.0           # multiplies the grid crowd cost
    stub_px: int = 22                  # mandatory perpendicular pin escape length
    body_clearance: float = 14.0       # default keep-out halo around a component body
    body_skirt_cost: float = 2.5       # soft cost just outside a body's clearance
    label_soft_cost: float = 16.0      # soft cost over a label's area (wires route around text)
    wire_halo: int = 1                 # committed-wire crowd halo radius (cells)
    wire_halo_cost: float = 3.0        # soft cost in that halo (keeps wires a track apart)
    wire_self_cost: float = 6.0        # cost to cross a committed wire (allows clean crossings)


@dataclass
class DrcConfig:
    min_wire_spacing: float = 9.0      # px; parallel different-net wires must stay ≥ this apart
    strict: bool = True                # True -> spacing warnings are hard failures too
    port_tolerance: float = 3.0        # px; how close a wire end must land on a pin


@dataclass
class RenderConfig:
    bg: tuple = (250, 250, 248)


@dataclass
class Config:
    router: RouterConfig = field(default_factory=RouterConfig)
    drc: DrcConfig = field(default_factory=DrcConfig)
    render: RenderConfig = field(default_factory=RenderConfig)

    @classmethod
    def from_dict(cls, d: dict | None) -> "Config":
        """Build from a flat or nested dict (JSON `config` block). Flat keys are
        routed to the right section, so `{"pitch": 12, "min_wire_spacing": 8}`
        works as well as `{"router": {"pitch": 12}}`."""
        cfg = cls()
        if not d:
            return cfg
        sections = {"router": cfg.router, "drc": cfg.drc, "render": cfg.render}
        for k, v in d.items():
            if k in sections and isinstance(v, dict):
                for kk, vv in v.items():
                    _set(sections[k], kk, vv)
            else:
                for sec in sections.values():          # flat key -> find its section
                    if hasattr(sec, k):
                        _set(sec, k, v)
                        break
        return cfg

    def to_dict(self) -> dict:
        return {"router": asdict(self.router), "drc": asdict(self.drc),
                "render": asdict(self.render)}


def _set(section, key, value):
    if hasattr(section, key):
        if key == "bg" and isinstance(value, (list, tuple)):
            value = tuple(value)
        setattr(section, key, value)
