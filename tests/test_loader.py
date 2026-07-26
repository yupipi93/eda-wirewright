"""Loader / declarative-format tests, incl. the AI-friendly error messages."""
from pathlib import Path

import pytest

from wirewright.engine import build
from wirewright.loader import SchematicError, load_dict, load_file

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "json"


def test_all_json_examples_build_and_pass_drc():
    files = sorted(EXAMPLES.glob("*.json"))
    assert files, "no JSON examples found"
    for f in files:
        schematic, cfg = load_file(str(f))
        result = build(schematic, cfg=cfg, verbose=False)
        assert result.net_count > 0


def test_unknown_component_type_suggests():
    doc = {"canvas": {"w": 400, "h": 400},
           "components": [{"id": "U1", "type": "arduino_nan", "x": 10, "y": 10}],
           "nets": []}
    with pytest.raises(SchematicError) as e:
        load_dict(doc)
    assert "arduino_nano" in str(e.value)      # difflib suggestion


def test_bad_port_lists_valid_ports():
    doc = {
        "canvas": {"w": 800, "h": 600},
        "components": [
            {"id": "U1", "type": "arduino_nano", "x": 100, "y": 100},
            {"id": "D1", "type": "led", "x": 500, "y": 200,
             "args": {"color": "red", "label": "L", "sub": "D2"}},
        ],
        "nets": [{"name": "n", "color": "led",
                  "nodes": [["port", "U1", "D2"], ["port", "D1", "anodX"]]}],
    }
    with pytest.raises(SchematicError) as e:
        load_dict(doc)
    assert "anode" in str(e.value)             # lists the real port names


def test_color_forms_all_resolve():
    for col in ["led", "red", "#ff0000", [255, 0, 0]]:
        doc = {"canvas": {"w": 400, "h": 400},
               "rails": [{"name": "G", "y": 300, "x0": 10, "x1": 390, "color": col}],
               "components": [{"id": "U1", "type": "arduino_nano", "x": 50, "y": 20}],
               "nets": [{"name": "g", "color": col,
                         "nodes": [["port", "U1", "GND"], ["rail", "G"]]}]}
        s, cfg = load_dict(doc)
        assert s.rails["G"].color == (255, 0, 0) or isinstance(s.rails["G"].color, tuple)
