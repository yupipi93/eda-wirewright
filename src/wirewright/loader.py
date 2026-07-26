"""Load a declarative schematic (dict / JSON) into a Schematic + Config.

This is the interface an AI model uses: emit a JSON contract, get a diagram.
Errors are raised as `SchematicError` with human-readable, fixable messages
(e.g. "component 'U1' type 'arduino_nan' unknown — did you mean arduino_nano?").

Format (see docs/contract-format.md and schema/schematic.schema.json):

    {
      "canvas": {"w":1400,"h":1000,"title":"…","subtitle":"…","bg":[250,250,248]},
      "config": {"pitch":10,"bend_penalty":14},
      "rails":  [{"name":"GND","y":820,"x0":80,"x1":1320,"color":"black","label":"GND"}],
      "components":[{"id":"U1","type":"arduino_nano","x":500,"y":300,"args":{}}],
      "nets":   [{"name":"n1","color":"led","nodes":[["port","U1","D2"],["port","D1","anode"]]}],
      "legend": {"x":80,"y":900,"w":1240,"h":80,"entries":[["led","LEDs",["…"]]],"notes":[]},
      "notes":  [{"x":100,"y":100,"text":"…","color":"muted"}],
      "annotations":[{"type":"dashed_arrow","x0":0,"y0":0,"x1":0,"y1":40,"color":"key","label":"…"}]
    }

Net node forms: ["port", comp_id, port] · ["rail", rail_name] · ["point", x, y]
Colours: a palette name ("led","gnd",…), a common name ("red"), "#rrggbb", or [r,g,b].
"""
from __future__ import annotations

import difflib
import json

from . import decorations as deco
from .config import Config
from .model import PointRef, PortRef, Rail, RailRef, Schematic
from .registry import COLOR_ARGS, REGISTRY
from .theme import resolve_color


class SchematicError(ValueError):
    pass


def _req(d, key, ctx):
    if key not in d:
        raise SchematicError(f"{ctx}: missing required field {key!r}")
    return d[key]


def load_json(text) -> tuple:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SchematicError(f"invalid JSON: {e}")
    return load_dict(data)


def load_file(path) -> tuple:
    with open(path, "r", encoding="utf-8") as f:
        return load_json(f.read())


def load_dict(data: dict) -> tuple:
    """Return (Schematic, Config)."""
    if not isinstance(data, dict):
        raise SchematicError("top level must be a JSON object")
    canvas = data.get("canvas", {})
    s = Schematic(
        w=int(_req(canvas, "w", "canvas")),
        h=int(_req(canvas, "h", "canvas")),
        title=canvas.get("title", ""),
        subtitle=canvas.get("subtitle", ""),
        bg=tuple(canvas.get("bg", (250, 250, 248))),
    )
    cfg = Config.from_dict(data.get("config"))

    # rails
    for r in data.get("rails", []):
        s.add_rail(Rail(
            name=_req(r, "name", "rail"),
            y=r["y"], x0=r["x0"], x1=r["x1"],
            color=resolve_color(_req(r, "color", f"rail {r.get('name')}")),
            label=r.get("label", ""),
            label_x=r.get("label_x"),
            width=r.get("width", 7),
        ))

    # components
    for c in data.get("components", []):
        cid = _req(c, "id", "component")
        ctype = _req(c, "type", f"component {cid}")
        if ctype not in REGISTRY:
            hint = difflib.get_close_matches(ctype, REGISTRY, n=1)
            extra = f" — did you mean {hint[0]!r}?" if hint else ""
            raise SchematicError(f"component {cid!r}: unknown type {ctype!r}{extra}. "
                                 f"Known: {', '.join(sorted(REGISTRY))}")
        args = dict(c.get("args", {}))
        for k in list(args):
            if k in COLOR_ARGS:
                args[k] = resolve_color(args[k])
        try:
            comp = REGISTRY[ctype](cid, c["x"], c["y"], **args)
        except TypeError as e:
            raise SchematicError(f"component {cid!r} ({ctype}): bad args — {e}")
        except KeyError as e:
            raise SchematicError(f"component {cid!r}: missing {e}")
        s.add(comp)

    # nets
    for n in data.get("nets", []):
        name = _req(n, "name", "net")
        color = resolve_color(_req(n, "color", f"net {name}"))
        nodes = [_node(nd, name, s) for nd in _req(n, "nodes", f"net {name}")]
        if len(nodes) < 2:
            raise SchematicError(f"net {name!r}: needs at least 2 nodes")
        s.connect(name, color, *nodes, width=n.get("width", 5),
                  style=n.get("style", "wire"), priority=n.get("priority", 0))

    # decorations
    _decorations(data, s)
    return s, cfg


def _node(nd, net_name, s):
    if not isinstance(nd, (list, tuple)) or not nd:
        raise SchematicError(f"net {net_name!r}: bad node {nd!r}")
    kind = nd[0]
    if kind == "port":
        if nd[1] not in s.components:
            raise SchematicError(f"net {net_name!r}: node references unknown component {nd[1]!r}")
        comp = s.components[nd[1]]
        if nd[2] not in comp.ports:
            raise SchematicError(f"net {net_name!r}: {nd[1]!r} has no port {nd[2]!r} "
                                 f"(has: {', '.join(comp.ports)})")
        return PortRef(nd[1], nd[2])
    if kind == "rail":
        if nd[1] not in s.rails:
            raise SchematicError(f"net {net_name!r}: unknown rail {nd[1]!r}")
        return RailRef(nd[1])
    if kind == "point":
        return PointRef(float(nd[1]), float(nd[2]))
    raise SchematicError(f"net {net_name!r}: node kind {kind!r} must be port|rail|point")


def _decorations(data, s):
    leg = data.get("legend")
    if leg:
        entries = [(resolve_color(e[0]), e[1], e[2] if len(e) > 2 else [])
                   for e in leg.get("entries", [])]
        notes = [tuple([n[0], resolve_color(n[1])]) if isinstance(n, list) else n
                 for n in leg.get("notes", [])]
        s.decorations.append(deco.legend(leg["x"], leg["y"], leg["w"], leg["h"],
                                         entries=entries, notes=notes))
    for nt in data.get("notes", []):
        s.decorations.append(deco.note(nt["x"], nt["y"], nt["text"],
                                       color=resolve_color(nt["color"]) if "color" in nt else None,
                                       font=nt.get("font", "pinsm"),
                                       anchor=nt.get("anchor", "lm")))
    for an in data.get("annotations", []):
        if an.get("type") == "dashed_arrow":
            s.decorations.append(deco.dashed_arrow(
                an["x0"], an["y0"], an["x1"], an["y1"],
                resolve_color(an.get("color", "gnd")), label=an.get("label")))
