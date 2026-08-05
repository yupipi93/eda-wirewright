# Changelog

All notable changes to wirewright. Format loosely follows Keep a Changelog.

## [Unreleased]

### Added
- **Battery + audio component family** in the library: `battery` (1S Li-ion /
  LiPo pouch with its two soldered leads, ports `pos`/`neg`),
  `power_bank_module` (IP5356-class boost + charger with a 2-digit fuel gauge,
  ports `batp`/`batn` west and `vout`/`gnd` east — the enable button and charge
  connector are drawn but are deliberately *not* ports, so the DRC does not
  demand wires for them), `amp_module` (LM386-class mono breakout with gain
  trimmer and speaker screw terminal, ports `sig`/`vcc`/`gnd`/`out`) and
  `speaker` (moving-coil driver, ports `p`/`n`). Registered + self-describing;
  covered by `tests/test_battery_audio_components.py`. First consumer:
  arduino-lemon-piano V6's battery + amplified-speaker diagram.
  - `amp_module`'s `gnd` port sits 112 px east of centre on purpose: its caption
    is centred under the same edge, and a centred port's escape stub struck
    through the text (caught in V6's first render, now a regression test).
- **`deco.panel(x, y, w, h, title, rows, accent=…)`** — a titled text box for
  prose that belongs *on* the drawing rather than in the legend: a mode table, a
  build warning, an operating note. `rows` accepts `""` for a blank line,
  `("h", text)` for an accent-coloured sub-heading, and `text` or
  `(text, colour)` for body lines.

- **Power-entry component family** in the library: `capacitor` (radial can /
  ceramic disc, `polarized` flag), `inductor` (drum choke), `diode` (axial body
  with cathode band, `flip` to swap ends — TVS clamps hang cathode-up) and
  `power_jack` (source box with `vout`/`gnd`). Registered + self-describing;
  covered by `tests/test_power_components.py`. First consumer:
  arduino-lemon-piano V5.5's filtered-supply diagram.

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
