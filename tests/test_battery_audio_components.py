"""The battery + audio family (battery / power_bank_module / amp_module /
speaker) — added for portable, amplified builds (arduino-lemon-piano V6). A
representative cell → boost module → amp → speaker chain must route and pass DRC
end to end, including the two module ports that face N/S rather than E/W."""
from wirewright.engine import build
from wirewright.loader import load_dict
from wirewright.registry import describe

NEW_TYPES = {
    "battery": {"pos", "neg"},
    "power_bank_module": {"batp", "batn", "vout", "gnd"},
    "amp_module": {"sig", "vcc", "gnd", "out"},
    "speaker": {"p", "n"},
}


def test_new_types_are_registered_with_ports():
    for t, want_ports in NEW_TYPES.items():
        d = describe(t)
        assert d["doc"], f"{t} has no DOC line"
        assert set(d["ports"]) == want_ports, f"{t} ports {d['ports']}"


def test_battery_to_speaker_chain_routes():
    """Cell → module → amp → speaker, with the amp's supply taken straight off
    the module (the V6 topology: the amplifier must not share a series element
    with the sensitive rail)."""
    doc = {
        "canvas": {"w": 2200, "h": 1200},
        "rails": [{"name": "GND", "y": 1000, "x0": 60, "x1": 2140, "color": "gnd"}],
        "components": [
            {"id": "BAT", "type": "battery", "x": 80, "y": 120},
            {"id": "IP1", "type": "power_bank_module", "x": 700, "y": 190},
            {"id": "AMP", "type": "amp_module", "x": 1400, "y": 600},
            {"id": "SPK", "type": "speaker", "x": 1900, "y": 600},
        ],
        "nets": [
            {"name": "batp", "color": "brown",
             "nodes": [["port", "BAT", "pos"], ["port", "IP1", "batp"]]},
            {"name": "batn", "color": "gnd",
             "nodes": [["port", "BAT", "neg"], ["port", "IP1", "batn"]]},
            {"name": "vbus", "color": "ctrl",
             "nodes": [["port", "IP1", "vout"], ["port", "AMP", "vcc"]]},
            {"name": "ipgnd", "color": "gnd",
             "nodes": [["port", "IP1", "gnd"], ["rail", "GND"]]},
            {"name": "sig", "color": "buzz",
             "nodes": [["port", "AMP", "sig"], ["point", 1120, 600]]},
            {"name": "ampgnd", "color": "gnd",
             "nodes": [["port", "AMP", "gnd"], ["rail", "GND"]]},
            {"name": "spk", "color": "buzz",
             "nodes": [["port", "AMP", "out"], ["port", "SPK", "p"]]},
            {"name": "spkret", "color": "gnd",
             "nodes": [["port", "SPK", "n"], ["rail", "GND"]]},
        ],
    }
    s, cfg = load_dict(doc)
    result = build(s, cfg=cfg, verbose=False)
    assert result.net_count == 8


def test_module_captions_clear_their_own_ports():
    """`amp_module`'s caption is centred under the body while `gnd` leaves the
    same edge; the port must sit east of the text so the escape stub does not
    strike through it (the defect that shipped in V6's first render)."""
    from wirewright import lib

    amp = lib.amp_module("AMP", 1000, 500)
    caption_boxes = amp.label_boxes
    assert caption_boxes, "amp_module must expose its caption as a DRC box"
    gnd_x = amp.port("gnd").x
    for box in caption_boxes:
        assert gnd_x > box.x1, f"gnd stub at x={gnd_x} runs through caption {box}"
