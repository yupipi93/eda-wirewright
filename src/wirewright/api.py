"""HTTP API — POST a schematic contract, get back a PNG.

Designed for agents and curl alike:
  GET  /                     service info + endpoint list
  GET  /health               liveness
  GET  /components           component catalogue (discover types/ports/params)
  GET  /openapi.json         OpenAPI 3 spec (so an agent can self-configure)
  POST /validate             route + DRC only → JSON result (no image)
  POST /render               route + DRC + render → PNG (or JSON with base64)

`/render` returns `image/png` by default; ask for JSON with
`Accept: application/json` or `?format=json` (handy for agents that want the
image as base64 plus the DRC report). Errors are always structured JSON with the
right HTTP status, so a caller can fix a bad contract and retry.

Run locally:   gunicorn wirewright.api:app -b 0.0.0.0:8080
               (or: python -m wirewright.api  →  dev server)
"""
from __future__ import annotations

import base64
import io

from flask import Flask, Response, jsonify, request

from . import __version__
from .config import Config
from .engine import DRCError, build
from .loader import SchematicError, load_dict
from .registry import describe_all


def _cfg_from(contract, args) -> Config:
    """Contract `config` block, overridable by ?pitch=&bend=&spacing= query args."""
    cfg = Config.from_dict(contract.get("config"))
    if args.get("pitch"):
        cfg.router.pitch = int(args["pitch"])
    if args.get("bend"):
        cfg.router.bend_penalty = float(args["bend"])
    if args.get("spacing"):
        cfg.drc.min_wire_spacing = float(args["spacing"])
    if args.get("strict") in ("0", "false", "no"):
        cfg.drc.strict = False
    return cfg


def _run(req):
    """Parse + build. Returns (report_dict, schematic_or_None, http_status)."""
    contract = req.get_json(silent=True)
    if contract is None:
        return {"status": "error",
                "error": "body must be a JSON schematic contract "
                         "(Content-Type: application/json)"}, None, 400
    try:
        schematic, _ = load_dict(contract)
        cfg = _cfg_from(contract, req.args)
    except SchematicError as e:
        return {"status": "invalid_contract", "error": str(e)}, None, 400
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}, None, 400
    try:
        result = build(schematic, cfg=cfg, verbose=False)
    except DRCError as e:
        return ({"status": "drc_failed",
                 "violations": [{"kind": v.kind, "msg": v.msg, "where": list(v.where)}
                                for v in e.violations]}, None, 422)
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}, None, 500
    report = {"status": "ok", "nets": result.net_count,
              "warnings": len(result.soft),
              "spacing_warnings": [v.msg for v in result.soft]}
    return report, schematic, 200


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024   # 4 MB contract cap

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "wirewright", "version": __version__}

    @app.get("/")
    def root():
        return {
            "service": "wirewright",
            "version": __version__,
            "description": "Declarative schematic engine — POST a contract, get a wiring-diagram PNG.",
            "endpoints": {
                "GET /components": "list component types, ports and params",
                "GET /openapi.json": "OpenAPI 3 spec",
                "POST /validate": "route + DRC only → JSON",
                "POST /render": "route + DRC + render → PNG (or JSON with ?format=json)",
            },
            "example": "curl -X POST $URL/render -H 'Content-Type: application/json' "
                       "-d @schematic.json -o out.png",
            "docs": "https://github.com/yupipi93/eda-wirewright",
        }

    @app.get("/components")
    def components():
        return jsonify(describe_all())

    @app.get("/openapi.json")
    def openapi():
        return jsonify(_OPENAPI)

    @app.post("/validate")
    def validate():
        report, _schematic, code = _run(request)
        return jsonify(report), code

    @app.post("/render")
    def render():
        report, schematic, code = _run(request)
        if code != 200:
            return jsonify(report), code
        buf = io.BytesIO()
        schematic._painter.img.save(buf, format="PNG")
        png = buf.getvalue()
        wants_json = ("application/json" in request.headers.get("Accept", "")
                      or request.args.get("format") == "json")
        if wants_json:
            report["image_base64"] = base64.b64encode(png).decode()
            report["content_type"] = "image/png"
            return jsonify(report), 200
        return Response(png, mimetype="image/png",
                        headers={"X-Wirewright-Nets": str(report["nets"]),
                                 "X-Wirewright-Warnings": str(report["warnings"])})

    return app


_BODY = {"required": True, "content":
         {"application/json": {"schema": {"$ref": "#/components/schemas/Contract"}}}}

_OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "wirewright", "version": __version__,
             "description": "POST a declarative schematic contract; get a validated wiring-diagram PNG. "
                            "See GET /components for component types and "
                            "https://github.com/yupipi93/eda-wirewright/blob/main/docs/contract-format.md."},
    "paths": {
        "/components": {"get": {
            "summary": "List component types, ports and params",
            "responses": {"200": {"description": "catalogue"}}}},
        "/validate": {"post": {
            "summary": "Route + DRC only",
            "requestBody": _BODY,
            "responses": {"200": {"description": "ok"},
                          "400": {"description": "invalid contract"},
                          "422": {"description": "DRC failed"}}}},
        "/render": {"post": {
            "summary": "Route + DRC + render to PNG",
            "parameters": [{"name": "format", "in": "query", "required": False,
                            "schema": {"type": "string", "enum": ["png", "json"]},
                            "description": "png (image bytes, default) or json (base64 + report)"}],
            "requestBody": _BODY,
            "responses": {"200": {"description": "PNG image or JSON",
                                  "content": {"image/png": {}, "application/json": {}}},
                          "400": {"description": "invalid contract"},
                          "422": {"description": "DRC failed (violations[])"}}}},
    },
    "components": {"schemas": {"Contract": {
        "type": "object", "required": ["canvas", "components", "nets"],
        "properties": {
            "canvas": {"type": "object"}, "config": {"type": "object"},
            "rails": {"type": "array"}, "components": {"type": "array"},
            "nets": {"type": "array"}, "legend": {"type": "object"},
            "notes": {"type": "array"}, "annotations": {"type": "array"},
        },
        "description": "Declarative schematic. Full field reference: docs/contract-format.md",
    }}},
}


app = create_app()


if __name__ == "__main__":       # dev server only; production uses gunicorn
    app.run(host="0.0.0.0", port=8080)
