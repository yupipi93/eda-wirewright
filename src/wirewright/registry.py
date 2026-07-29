"""Component registry — maps a declarative `type` name to a library factory, and
introspects each factory's parameters so the CLI / MCP / AI can discover exactly
what a component accepts. This is what makes the JSON format self-describing."""
from __future__ import annotations

import inspect

from . import library as lib

# declarative type name -> factory(id, x, y, **args)
REGISTRY = {
    "arduino_nano": lib.arduino_nano,
    "lemon_key": lib.lemon_key,
    "resistor": lib.resistor,
    "led": lib.led,
    "buzzer": lib.buzzer,
    "push_button": lib.push_button,
    "spdt_switch": lib.spdt_switch,
    "relay_module": lib.relay_module,
    "water_pump": lib.water_pump,
    "clip_box": lib.clip_box,
    "ultrasonic": lib.ultrasonic,
    "capacitor": lib.capacitor,
    "inductor": lib.inductor,
    "diode": lib.diode,
    "power_jack": lib.power_jack,
}

# args whose value is a colour (resolved through theme.resolve_color by the loader)
COLOR_ARGS = {"color", "cap"}

# one-line human summaries (shown by `wirewright components`)
DOC = {
    "arduino_nano": "Arduino Nano — 30 pins (VIN..D12, A0..A7); ports named by pin.",
    "lemon_key": "A fruit/touch key; one port 'clip'.",
    "resistor": "2-terminal resistor; ports 'a','b'. orient 'H'|'V'.",
    "led": "LED; ports 'anode','cathode'. anode/cathode facing 'N'|'S'|'E'|'W'.",
    "buzzer": "Passive buzzer; ports 'sig','gnd'.",
    "push_button": "Momentary button; ports 'pin','v5'.",
    "spdt_switch": "SPDT selector; ports 'com','p5','pg'. com_facing 'W'|'E'.",
    "relay_module": "Relay module; ports 'IN1'[,'IN2'],'VCC','GND','OUT' (channels=1|2).",
    "water_pump": "Pump load; port 'in'.",
    "clip_box": "Hand-held clip / labelled source box; port 'out'.",
    "ultrasonic": "HC-SR04 ultrasonic module; ports 'vcc','gnd','trig','echo'.",
    "capacitor": "Capacitor; ports 'a','b' ('a' is + when polarized). orient 'H'|'V'.",
    "inductor": "Power choke / ferrite; ports 'a','b'. orient 'H'|'V'.",
    "diode": "Diode (rectifier/Schottky/TVS); ports 'anode','cathode'. orient 'H'|'V'.",
    "power_jack": "Power source box; ports 'vout','gnd' on the E side.",
}


def describe(type_name):
    """Return {type, doc, params:[{name, required, default}], ports:[...]}."""
    fn = REGISTRY[type_name]
    sig = inspect.signature(fn)
    params = []
    for name, p in sig.parameters.items():
        if name in ("id", "x", "y"):
            continue
        params.append({
            "name": name,
            "required": p.default is inspect.Parameter.empty,
            "default": None if p.default is inspect.Parameter.empty else p.default,
            "is_color": name in COLOR_ARGS,
        })
    # probe port names by building a throwaway instance at the origin
    try:
        comp = fn("_probe", 0, 0, **{p["name"]: p["default"]
                                     for p in params if not p["required"] and p["default"] is not None})
        ports = list(comp.ports.keys())
    except Exception:
        ports = []
    return {"type": type_name, "doc": DOC.get(type_name, ""), "params": params, "ports": ports}


def describe_all():
    return [describe(t) for t in REGISTRY]
