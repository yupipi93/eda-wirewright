"""DRC unit tests — the guarantees the whole engine exists to provide. We feed
the validator synthetic routes so each failure class is deterministic."""
from wirewright import validator as drc
from wirewright.config import Config
from wirewright.geometry import BBox
from wirewright.model import Component, Net, Port, PortRef, Schematic
from wirewright.router import RouteResult


def _stub_component(cid, box, ports):
    return Component(cid, box, ports, draw=lambda p: None)


def _routed(polylines):
    r = RouteResult()
    r.polylines = polylines
    return r


def test_wire_over_component_is_caught():
    s = Schematic(500, 500)
    s.add(_stub_component("B", BBox(100, 100, 200, 200), {}))
    net = Net("n", (0, 0, 0), [])
    hard, _ = drc.check(s, [(net, _routed([[(50, 150), (250, 150)]]))], Config())
    assert any(v.kind == "wire-over-component" for v in hard)


def test_coincident_wires_caught():
    s = Schematic(500, 500)
    a = Net("a", (0, 0, 0), [])
    b = Net("b", (0, 0, 0), [])
    seg = [[(10, 10), (200, 10)]]
    hard, _ = drc.check(s, [(a, _routed(seg)), (b, _routed(seg))], Config())
    assert any(v.kind == "coincident-wires" for v in hard)


def test_unconnected_pin_caught():
    s = Schematic(500, 500)
    s.add(_stub_component("R", BBox(300, 300, 320, 360),
                          {"a": Port("a", 310, 300, "N")}))
    net = Net("n", (0, 0, 0), [PortRef("R", "a")])
    # a route that does NOT reach the pin at (310,300)
    hard, _ = drc.check(s, [(net, _routed([[(10, 10), (100, 10)]]))], Config())
    assert any(v.kind == "unconnected-pin" for v in hard)


def test_clean_route_passes():
    s = Schematic(500, 500)
    s.add(_stub_component("R", BBox(300, 300, 320, 360),
                          {"a": Port("a", 310, 300, "N")}))
    net = Net("n", (0, 0, 0), [PortRef("R", "a")])
    hard, _ = drc.check(s, [(net, _routed([[(310, 300), (310, 100)]]))], Config())
    assert hard == []
