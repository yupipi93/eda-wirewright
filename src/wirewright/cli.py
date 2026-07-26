"""`wirewright` command-line interface.

    wirewright render  schematic.json -o out.png [--pitch N] [--bend N] [--json]
    wirewright validate schematic.json [--json]        # DRC only, no file written
    wirewright components [--json]                      # list component types + params
    wirewright version

Designed to be script- and AI-friendly: `--json` makes every command emit a
single machine-readable object (status, output path, net count, warnings, and
structured DRC violations) so a caller can act on failures programmatically."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import Config
from .engine import DRCError, build, save
from .loader import SchematicError, load_file
from .registry import describe_all


def _apply_overrides(cfg: Config, args):
    if args.pitch is not None:
        cfg.router.pitch = args.pitch
    if args.bend is not None:
        cfg.router.bend_penalty = args.bend
    if args.spacing is not None:
        cfg.drc.min_wire_spacing = args.spacing
    if args.no_strict:
        cfg.drc.strict = False
    return cfg


def _emit(obj, as_json):
    if as_json:
        print(json.dumps(obj, default=str))
    else:
        status = obj.get("status")
        if status == "ok":
            out = obj.get("output")
            print(f"OK — {obj.get('nets')} nets, {obj.get('warnings',0)} warning(s)"
                  + (f" → {out}" if out else ""))
        elif status == "drc_failed":
            print(f"DRC FAILED — {len(obj['violations'])} violation(s):", file=sys.stderr)
            for v in obj["violations"]:
                print(f"  - [{v['kind']}] {v['msg']}", file=sys.stderr)
        else:
            print(f"ERROR: {obj.get('error')}", file=sys.stderr)


def _build_common(args):
    """Load + build; returns (result_obj, exit_code)."""
    try:
        schematic, cfg = load_file(args.input)
    except (SchematicError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}, 2
    _apply_overrides(cfg, args)
    try:
        result = build(schematic, cfg=cfg, verbose=False)
    except DRCError as e:
        return {"status": "drc_failed",
                "violations": [{"kind": v.kind, "msg": v.msg, "where": v.where}
                               for v in e.violations]}, 1
    except Exception as e:                      # unexpected (routing/geometry)
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}, 3
    return {"status": "ok", "schematic": schematic, "result": result,
            "nets": result.net_count, "warnings": len(result.soft)}, 0


def cmd_render(args):
    obj, code = _build_common(args)
    if obj["status"] == "ok":
        out = args.output or _default_out(args.input)
        save(obj.pop("schematic"), out)
        obj.pop("result", None)
        obj["output"] = out
    _emit(obj, args.json)
    return code


def cmd_validate(args):
    obj, code = _build_common(args)
    obj.pop("schematic", None)
    obj.pop("result", None)
    _emit(obj, args.json)
    return code


def cmd_components(args):
    comps = describe_all()
    if args.json:
        print(json.dumps(comps, default=str, indent=2))
    else:
        for c in comps:
            print(f"{c['type']:<14} {c['doc']}")
            if c["ports"]:
                print(f"{'':14} ports: {', '.join(c['ports'])}")
            opt = [p["name"] + (f"={p['default']}" if p["default"] is not None else "")
                   for p in c["params"] if not p["required"]]
            req = [p["name"] for p in c["params"] if p["required"]]
            if req:
                print(f"{'':14} required: {', '.join(req)}")
            if opt:
                print(f"{'':14} optional: {', '.join(opt)}")
    return 0


def _default_out(input_path):
    return input_path.rsplit(".", 1)[0] + ".png"


def build_parser():
    p = argparse.ArgumentParser(prog="wirewright",
                                description="Declarative schematic engine — auto-route + DRC.")
    p.add_argument("--version", action="version", version=f"wirewright {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("input", help="schematic .json contract")
        sp.add_argument("--pitch", type=int, help="routing-grid pitch (px)")
        sp.add_argument("--bend", type=float, help="bend penalty (higher = straighter)")
        sp.add_argument("--spacing", type=float, help="min wire spacing DRC (px)")
        sp.add_argument("--no-strict", action="store_true", help="spacing warnings non-fatal")
        sp.add_argument("--json", action="store_true", help="machine-readable output")

    r = sub.add_parser("render", help="route + validate + write a PNG")
    add_common(r)
    r.add_argument("-o", "--output", help="output PNG (default: alongside input)")
    r.set_defaults(func=cmd_render)

    v = sub.add_parser("validate", help="route + DRC only (no file written)")
    add_common(v)
    v.set_defaults(func=cmd_validate)

    c = sub.add_parser("components", help="list available component types")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_components)

    sub.add_parser("version", help="print version").set_defaults(
        func=lambda a: (print(__version__), 0)[1])
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
