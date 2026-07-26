# The declarative contract format

A schematic is a single JSON object with up to seven top-level keys. Only
`canvas`, `components` and `nets` are required. Validated by
[`schema/schematic.schema.json`](../schema/schematic.schema.json).

```jsonc
{
  "canvas":     { … },   // required — size + titles
  "config":     { … },   // optional — engine knobs
  "rails":      [ … ],   // optional — power/ground buses
  "components": [ … ],   // required — the parts
  "nets":       [ … ],   // required — the connections
  "legend":     { … },   // optional — colour key box
  "notes":      [ … ],   // optional — free-text labels
  "annotations":[ … ]    // optional — dashed arrows etc.
}
```

## `canvas`

| field | type | notes |
|---|---|---|
| `w`, `h` | int | canvas size in px (required) |
| `title`, `subtitle` | string | centered at the top |
| `bg` | `[r,g,b]` | background colour (default warm white) |

## `config` (optional)

Flat or nested by section. Any of:
`pitch`, `bend_penalty`, `proximity_k`, `stub_px`, `body_clearance`,
`body_skirt_cost`, `label_soft_cost`, `wire_halo`, `wire_halo_cost`,
`wire_self_cost` (router); `min_wire_spacing`, `strict`, `port_tolerance` (drc);
`bg` (render).

```json
"config": {"pitch": 12, "bend_penalty": 20, "min_wire_spacing": 8}
```

## `rails`

Horizontal power/ground buses. Connect to them from a net with `["rail","NAME"]`.

| field | type | notes |
|---|---|---|
| `name` | string | referenced by nets |
| `y`, `x0`, `x1` | number | the horizontal line |
| `color` | colour | see colours below |
| `label` | string | printed at the right end |
| `label_x` | number\|null | override label x |
| `width` | int | line thickness (default 7) |

## `components`

| field | type | notes |
|---|---|---|
| `id` | string | unique; referenced by nets |
| `type` | string | a registered type (`wirewright components`) |
| `x`, `y` | number | anchor position |
| `args` | object | extra constructor args for that type |

The engine places components where you say; it does **not** auto-place. Give each
its own horizontal band and leave a channel (~150–250 px) to the next.

Colour-valued args (`color`, `cap`) accept the same colour forms as everywhere.

## `nets`

A net is one electrical node. List **all** its terminals.

| field | type | notes |
|---|---|---|
| `name` | string | unique-ish label |
| `color` | colour | wire colour |
| `nodes` | array | ≥2 terminals |
| `width` | int | wire thickness (default 5) |
| `style` | `"wire"`\|`"label"` | `wire` = routed (default) |
| `priority` | int | lower routes first (default = span) |

**Node forms**

```
["port", "U1", "D13"]     a component port
["rail", "GND"]           anywhere along a rail
["point", 640, 480]       a fixed coordinate
```

## Colours

Anywhere a colour is expected: a **palette name**
(`v5`/`power`, `gnd`, `key`, `led`/`sig`, `ctrl`, `buzz`, `relay`, `margin`), a
**common name** (`red`, `green`, `blue`, `black`, `orange`, `purple`, `brown`,
`pink`, `yellow`, `grey`, plus `rojo`/`verde`/`azul`/…), a **hex** `"#rrggbb"`,
or an **`[r,g,b]`** triple.

## `legend` (optional)

```json
"legend": {
  "x": 90, "y": 870, "w": 1310, "h": 110,
  "entries": [["led", "Signal", ["D13 → LED anode"]],
              ["gnd", "Ground", ["cathode → 220 Ω → GND"]]],
  "notes": ["footnote line", ["coloured footnote", "muted"]]
}
```

Each entry is `[color, title, [rows…]]`.

## `notes` (optional)

```json
"notes": [{"x": 100, "y": 100, "text": "…", "color": "muted",
           "font": "pinsm", "anchor": "lm"}]
```

Fonts: `title`, `sub`, `mod`, `modsub`, `pin`, `pinsm`, `leg`, `legsm`, `tiny`.

## `annotations` (optional)

```json
"annotations": [{"type": "dashed_arrow", "x0": 300, "y0": 240,
                 "x1": 300, "y1": 280, "color": "key", "label": "touch"}]
```

## Result contract (CLI `--json`, MCP tools)

```jsonc
{"status": "ok", "nets": 5, "warnings": 0, "output": "out.png"}
{"status": "drc_failed", "violations": [{"kind": "...", "msg": "...", "where": [x, y]}]}
{"status": "invalid_contract", "error": "component 'U1': unknown type 'arduino_nan' — did you mean 'arduino_nano'?"}
{"status": "error", "error": "..."}
```
