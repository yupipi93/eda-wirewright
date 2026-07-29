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
        info = {
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
        # Browsers get a human landing page; API clients get JSON.
        if "text/html" in request.headers.get("Accept", ""):
            return Response(_LANDING.replace("__VERSION__", __version__), mimetype="text/html")
        return info

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


_LANDING = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>wirewright — schematic engine</title>
<style>
  :root{ --ink:#141414; --paper:#f4f3ee; --line:#141414; --muted:#5b5b57; --faint:#dedcd3; }
  *{ box-sizing:border-box; }
  html{ -webkit-text-size-adjust:100%; }
  body{
    margin:0; background:var(--paper); color:var(--ink);
    font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
    line-height:1.55; font-size:17px;
    background-image:radial-gradient(var(--faint) 0.5px, transparent 0.5px);
    background-size:4px 4px;            /* subtle e-ink dither */
  }
  .wrap{ max-width:720px; margin:0 auto; padding:56px 24px 72px; }
  header{ border-bottom:3px double var(--line); padding-bottom:18px; margin-bottom:26px; }
  .brand{ display:flex; align-items:center; gap:16px; }
  .brand svg{ flex:none; }
  h1{ font-size:40px; letter-spacing:-0.5px; margin:0; font-weight:700; }
  .tag{ margin:6px 0 0; font-style:italic; color:var(--muted); }
  .ver{ font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12px;
        border:1px solid var(--line); border-radius:2px; padding:1px 6px; font-style:normal; }
  h2{ font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12px;
      letter-spacing:2px; text-transform:uppercase; color:var(--muted);
      margin:34px 0 12px; }
  p{ margin:0 0 14px; } a{ color:var(--ink); text-decoration:underline; text-underline-offset:2px; }
  pre{ background:#fbfaf6; border:1px solid var(--line); border-radius:3px;
       padding:14px 16px; overflow-x:auto; font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
       font-size:13px; line-height:1.5; margin:0 0 14px; }
  code{ font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:0.85em; }
  figure{ margin:0 0 22px; }
  figure a{ display:block; border:1px solid var(--line); border-radius:3px; background:#fff; }
  figure img{ display:block; width:100%; height:auto; }
  figcaption{ font-size:14px; color:var(--muted); font-style:italic; margin-top:8px; }
  table{ width:100%; border-collapse:collapse; margin:0 0 14px; font-size:15px; }
  td{ border-top:1px solid var(--faint); padding:8px 6px; vertical-align:top; }
  td.m{ font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:13px; white-space:nowrap; }
  footer{ border-top:3px double var(--line); margin-top:40px; padding-top:16px;
          color:var(--muted); font-size:14px; display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }
  /* auto dark only when the visitor hasn't picked a theme via the toggle */
  @media (prefers-color-scheme:dark){
    :root:not([data-theme]){ --ink:#e9e7df; --paper:#15140f; --line:#e9e7df; --muted:#a7a49a; --faint:#2a2822; }
    :root:not([data-theme]) pre{ background:#1b1a14; }
  }
  :root[data-theme="dark"]{ --ink:#e9e7df; --paper:#15140f; --line:#e9e7df; --muted:#a7a49a; --faint:#2a2822; }
  :root[data-theme="dark"] pre{ background:#1b1a14; }
  #theme{ position:fixed; top:16px; right:16px; z-index:10;
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12px;
    background:var(--paper); color:var(--ink); border:1px solid var(--line);
    border-radius:2px; padding:6px 10px; cursor:pointer; line-height:1;
    letter-spacing:0.5px; }
  #theme:hover{ background:var(--faint); }
</style></head>
<body>
  <button id="theme" type="button" aria-label="Toggle light / dark theme">◐ theme</button>
  <div class="wrap">
  <header><div class="brand">
    <svg width="52" height="52" viewBox="0 0 52 52" fill="none" stroke="currentColor" stroke-width="2.4">
      <rect x="7" y="7" width="38" height="38" rx="3"/>
      <path d="M7 19 H1 M7 33 H1 M45 19 H51 M45 33 H51 M19 7 V1 M33 7 V1 M19 45 V51 M33 45 V51"/>
      <circle cx="26" cy="26" r="4.5" fill="currentColor" stroke="none"/>
    </svg>
    <div><h1>wirewright</h1>
      <p class="tag">declarative schematic engine · auto-router + DRC <span class="ver">v__VERSION__</span></p>
    </div>
  </div></header>

  <p>Describe <em>what connects to what</em> — components, typed ports, nets — and wirewright
     works out <em>how to draw it</em>: clean orthogonal wires that never cross a component
     body, never run on top of each other, never leave a pin unconnected, and keep their
     distance. Every diagram is <strong>design-rule-checked before it is returned</strong>.</p>

  <h2>Real output</h2>
  <figure>
    <a href="/static/lemon-piano-v5.png" title="Open full size">
      <img src="/static/lemon-piano-v5.png" loading="lazy"
           alt="Lemon Piano V5 wiring diagram — Arduino Nano, 7 touch keys, ten-LED bar, buzzer — rendered by wirewright"></a>
    <figcaption>The <a href="https://github.com/yupipi93/arduino-lemon-piano">Lemon&nbsp;Piano</a> V5
      wiring — seven touch keys, a ten-LED bar, live sensitivity buttons, buzzer — auto-routed and
      DRC-validated by wirewright from a declarative contract. Never hand-drawn. Click for full size.</figcaption>
  </figure>
  <figure>
    <a href="/static/oscilloscope-m6.png" title="Open full size">
      <img src="/static/oscilloscope-m6.png" loading="lazy"
           alt="Arduino oscilloscope M6 dual-channel wiring diagram — the hand-placed style wirewright automates"></a>
    <figcaption>For reference, the style wirewright grew out of: the
      <a href="https://github.com/yupipi93/arduino-oscilloscope-PG240128-A">Arduino oscilloscope</a>
      M6 dual-channel wiring, hand-placed pin by pin before wirewright existed. wirewright produces
      this look automatically — with routing and DRC guaranteed.</figcaption>
  </figure>

  <h2>Try it</h2>
  <pre>curl -X POST https://wirewright.scv.multitecua.com/render \\
     -H 'Content-Type: application/json' \\
     -d @circuit.json -o circuit.png</pre>
  <p>Agents: add <code>?format=json</code> to get the PNG as base64 plus the DRC report,
     or <code>POST /validate</code> for the DRC result alone. Discover the parts with
     <code>GET /components</code>; self-configure from <code>GET /openapi.json</code>.</p>

  <h2>Endpoints</h2>
  <table>
    <tr><td class="m">POST /render</td><td>route + DRC + render → <code>image/png</code> (or JSON+base64 with <code>?format=json</code>)</td></tr>
    <tr><td class="m">POST /validate</td><td>route + DRC only → JSON (<code>ok</code> / <code>drc_failed</code> / <code>invalid_contract</code>)</td></tr>
    <tr><td class="m">GET /components</td><td>component catalogue — types, ports, params</td></tr>
    <tr><td class="m">GET /openapi.json</td><td>OpenAPI 3 spec</td></tr>
    <tr><td class="m">GET /health</td><td>liveness</td></tr>
  </table>

  <h2>The contract</h2>
  <p>A schematic is a small JSON object (<code>canvas</code>, <code>rails</code>,
     <code>components</code>, <code>nets</code>). Errors come back structured and fixable —
     <em>"D1 has no port 'anodX' (has: anode, cathode)"</em> — so a caller can correct and
     retry. Full reference and examples on
     <a href="https://github.com/yupipi93/eda-wirewright/blob/main/docs/contract-format.md">GitHub</a>.</p>

  <footer>
    <span>renders on Cloud Run · stateless · MIT</span>
    <span><a href="https://github.com/yupipi93/eda-wirewright">github.com/yupipi93/eda-wirewright</a></span>
  </footer>
  </div>
  <script>
  (function(){
    var root=document.documentElement, btn=document.getElementById('theme');
    function eff(){ return root.getAttribute('data-theme') ||
      (window.matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light'); }
    function label(){ btn.textContent = eff()==='dark' ? '☀ light' : '☾ dark'; }
    try{ var s=localStorage.getItem('ww-theme'); if(s){ root.setAttribute('data-theme', s); } }catch(e){}
    label();
    btn.addEventListener('click', function(){
      var next = eff()==='dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try{ localStorage.setItem('ww-theme', next); }catch(e){}
      label();
    });
  })();
  </script>
</body></html>"""


app = create_app()


if __name__ == "__main__":       # dev server only; production uses gunicorn
    app.run(host="0.0.0.0", port=8080)
