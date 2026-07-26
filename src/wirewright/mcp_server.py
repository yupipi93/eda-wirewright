"""MCP server — exposes wirewright as tools an AI agent (e.g. Claude) can call.

Run:  wirewright-mcp            (stdio transport; add to an MCP client config)
      python -m wirewright.mcp_server

Requires the optional `mcp` extra:  pip install 'wirewright[mcp]'

Tools:
  * list_components()                     -> the component catalogue (self-describing)
  * validate_schematic(contract)          -> DRC result (no file written)
  * render_schematic(contract, path?)     -> PNG (base64 + optional file) or DRC errors

`contract` is the declarative JSON object documented in docs/contract-format.md.
Every result is structured so the model can fix a rejected contract and retry."""
from __future__ import annotations

import base64
import io

from .engine import DRCError, build
from .loader import SchematicError, load_dict
from .registry import describe_all


def _validate(contract: dict, strict: bool = True):
    try:
        schematic, cfg = load_dict(contract)
    except SchematicError as e:
        return {"status": "invalid_contract", "error": str(e)}, None, None
    cfg.drc.strict = strict
    try:
        result = build(schematic, cfg=cfg, verbose=False)
    except DRCError as e:
        return ({"status": "drc_failed",
                 "violations": [{"kind": v.kind, "msg": v.msg, "where": list(v.where)}
                                for v in e.violations]}, None, None)
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}, None, None
    return ({"status": "ok", "nets": result.net_count,
             "warnings": len(result.soft),
             "spacing_warnings": [{"kind": v.kind, "msg": v.msg} for v in result.soft]},
            schematic, result)


def make_server():
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("wirewright")

    @mcp.tool()
    def list_components() -> list:
        """List every component type, its ports, and its parameters. Use this to
        discover how to describe components in a contract."""
        return describe_all()

    @mcp.tool()
    def validate_schematic(contract: dict, strict: bool = True) -> dict:
        """Route + DRC a declarative schematic contract WITHOUT writing a file.
        Returns status 'ok' | 'drc_failed' | 'invalid_contract' | 'error' with
        structured violations you can use to fix the contract."""
        report, _, _ = _validate(contract, strict)
        return report

    @mcp.tool()
    def render_schematic(contract: dict, output_path: str = "", strict: bool = True) -> dict:
        """Route + DRC + render a schematic. On success returns the PNG as base64
        (and writes to output_path if given). On failure returns the same
        structured DRC/contract errors as validate_schematic."""
        report, schematic, _ = _validate(contract, strict)
        if report["status"] != "ok":
            return report
        buf = io.BytesIO()
        schematic._painter.img.save(buf, format="PNG")
        data = buf.getvalue()
        if output_path:
            with open(output_path, "wb") as f:
                f.write(data)
            report["output"] = output_path
        report["image_base64"] = base64.b64encode(data).decode()
        return report

    return mcp


def main():
    try:
        make_server().run()
    except ImportError:
        raise SystemExit("The MCP server needs the optional dependency. "
                         "Install with:  pip install 'wirewright[mcp]'")


if __name__ == "__main__":
    main()
