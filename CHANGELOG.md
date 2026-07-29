# Changelog

All notable changes to wirewright. Format loosely follows Keep a Changelog.

## [0.1.3] — 2026-07-29

### Added
- **Landing page examples** (`GET /` HTML): a "Real output" section with two
  static images served from the package (`/static/…`) — the Lemon Piano V5
  wiring (rendered by wirewright, DRC-validated) and, for reference, the
  hand-placed Arduino oscilloscope M6 diagram whose style wirewright automates.

## [0.1.0] — 2026-07-26

First release. Extracted from the arduino-lemon-piano project into a standalone,
reusable EDA tool.

### Added
- **Grid A\* auto-router** (`router.py`): orthogonal maze routing with a large
  bend penalty (straight lines), a light proximity penalty (spacing), mandatory
  pin escape stubs, multi-terminal Steiner-ish nets, and rail targets.
- **Geometric DRC** (`validator.py`): raises on wire-over-body, coincident
  wires, unconnected pins, and wires-too-close — a diagram with a fault won't
  build.
- **Declarative JSON contract format** (`loader.py` + `schema/`) with actionable,
  AI-friendly error messages; the component registry is self-describing.
- **CLI** `wirewright` (`render`, `validate`, `components`, `version`) with config
  flags and `--json` machine-readable output.
- **MCP server** `wirewright-mcp` (`list_components`, `validate_schematic`,
  `render_schematic`) for AI agents / Claude.
- **Parametrised** engine via `config.py` (`RouterConfig`/`DrcConfig`/
  `RenderConfig`), settable from JSON, CLI or Python.
- Component library: `arduino_nano`, `led`, `resistor`, `push_button`,
  `spdt_switch`, `buzzer`, `relay_module`, `water_pump`, `lemon_key`, `clip_box`.
- Packaging (`pyproject.toml`, src layout, console entry points), **Dockerfile**
  + compose, **Makefile**, **GitHub Actions CI** (lint + test 3.9–3.12 + render
  examples + docker build), pytest suite, docs and examples.
