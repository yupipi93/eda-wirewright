"""The power-entry family (capacitor / inductor / diode / power_jack) — added
for filtered-supply diagrams (arduino-lemon-piano V5.5). A representative pi
filter must route and pass DRC end to end, in both orientations."""
import pytest

from wirewright.engine import build
from wirewright.loader import load_dict
from wirewright.registry import describe

NEW_TYPES = {
    "capacitor": {"a", "b"},
    "inductor": {"a", "b"},
    "diode": {"anode", "cathode"},
    "power_jack": {"vout", "gnd"},
}


def test_new_types_are_registered_with_ports():
    for t, want_ports in NEW_TYPES.items():
        d = describe(t)
        assert d["doc"], f"{t} has no DOC line"
        assert set(d["ports"]) == want_ports, f"{t} ports {d['ports']}"


@pytest.mark.parametrize("orient", ["H", "V"])
def test_two_terminal_parts_route_in_both_orientations(orient):
    doc = {
        "canvas": {"w": 1400, "h": 900},
        "rails": [{"name": "GND", "y": 700, "x0": 60, "x1": 1340, "color": "gnd"}],
        "components": [
            {"id": "J1", "type": "power_jack", "x": 60, "y": 200},
            {"id": "L1", "type": "inductor", "x": 700, "y": 250, "args": {"orient": orient}},
            {"id": "D1", "type": "diode", "x": 500, "y": 420, "args": {"orient": orient}},
            {"id": "C1", "type": "capacitor", "x": 1000, "y": 420,
             "args": {"orient": orient, "polarized": True, "label": "470 µF"}},
        ],
        "nets": [
            {"name": "vin", "color": "power",
             "nodes": [["port", "J1", "vout"], ["port", "D1", "anode"], ["port", "L1", "a"]]},
            {"name": "vf", "color": "power",
             "nodes": [["port", "L1", "b"], ["port", "C1", "a"]]},
            {"name": "g1", "color": "gnd", "nodes": [["port", "J1", "gnd"], ["rail", "GND"]]},
            {"name": "g2", "color": "gnd", "nodes": [["port", "D1", "cathode"], ["rail", "GND"]]},
            {"name": "g3", "color": "gnd", "nodes": [["port", "C1", "b"], ["rail", "GND"]]},
        ],
    }
    s, cfg = load_dict(doc)
    result = build(s, cfg=cfg, verbose=False)
    assert result.net_count == 5
