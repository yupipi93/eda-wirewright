"""wirewright — declarative schematic / wiring-diagram engine with an automatic
orthogonal router and a geometric DRC.

You describe components, ports and nets (the *contract*); the engine auto-routes
wires that never cross a component body, never run coincident, never leave a pin
unconnected, and keep their distance — then it DRC-validates and renders to PNG.
Add components and nets and it composes any schematic; no hand-placed wire
coordinates.

Two ways in:
  * Python API (this module) — build a `Schematic` and call `build()`.
  * Declarative JSON (`wirewright.loader.load_dict`) — ideal for AI models and
    the `wirewright` CLI / MCP server.

Python quickstart:

    from wirewright import Schematic, lib, P, R, Rail, build, save, C

    s = Schematic(1400, 1000, title="LED")
    s.add_rail(Rail("GND", y=820, x0=80, x1=1320, color=C["gnd"], label="GND"))
    s.add(lib.arduino_nano("U1", 500, 300))
    s.add(lib.led("D1", 900, 360, C["led"], "LED", "D2", anode="W"))
    s.connect("n1", C["led"], P("U1", "D2"), P("D1", "anode"))
    s.connect("g",  C["gnd"], P("U1", "GND"), R("GND"))
    build(s); save(s, "led.png")
"""
from . import decorations as deco
from . import library as lib
from .config import Config, DrcConfig, RenderConfig, RouterConfig
from .engine import BuildResult, DRCError, build, save
from .model import PointRef, PortRef, Rail, RailRef, Schematic
from .model import PointRef as Pt
from .model import PortRef as P  # short aliases
from .model import RailRef as R
from .theme import PALETTE, C, resolve_color

__version__ = "0.1.3"

__all__ = [
    "Schematic", "Rail", "PortRef", "RailRef", "PointRef", "P", "R", "Pt",
    "lib", "C", "PALETTE", "resolve_color", "deco",
    "Config", "RouterConfig", "DrcConfig", "RenderConfig",
    "build", "save", "BuildResult", "DRCError", "__version__",
]
