# Using wirewright as an AI model

This file is the recipe for an LLM/agent to generate wiring diagrams reliably.
You produce a **JSON contract**; wirewright routes + validates + renders it.

## The loop

1. **Discover components.** Call `wirewright components --json` (CLI) or the
   `list_components` MCP tool. It returns every component `type`, its `ports`,
   and its `params` (name, required, default). Never guess a type, port, or
   arg name — read them from here.
2. **Write the contract** (schema below). Place components on a left→right flow;
   you choose coordinates, the engine does the wiring.
3. **Validate** with `wirewright validate contract.json --json` or the
   `validate_schematic` MCP tool. If `status != "ok"`, fix and retry:
   - `"invalid_contract"` → the `error` string tells you exactly what (unknown
     type with a suggestion, missing/typo'd port with the valid list, …).
   - `"drc_failed"` → `violations[]` lists geometric problems; the usual cause
     is a *modelling* error (see "Common fixes" below), not a bad coordinate.
4. **Render** with `wirewright render contract.json -o out.png` or
   `render_schematic` (returns base64 PNG).

## Contract shape (minimum)

```json
{
  "canvas": {"w": 1500, "h": 1000, "title": "…", "subtitle": "…"},
  "rails":  [{"name":"GND","y":820,"x0":90,"x1":1400,"color":"black","label":"GND"}],
  "components": [{"id":"U1","type":"arduino_nano","x":520,"y":300,"args":{}}],
  "nets": [{"name":"n1","color":"led","nodes":[["port","U1","D13"],["port","D1","anode"]]}]
}
```

- **Net node forms:** `["port", comp_id, port_name]` · `["rail", rail_name]` ·
  `["point", x, y]`. A net is one electrical node; give it **all** the terminals
  that are electrically the same (2, 3, or more).
- **Colours:** a palette name (`led`, `gnd`, `v5`, `ctrl`, `buzz`, `relay`,
  `margin`, `key`, `power`), a common name (`red`), `"#rrggbb"`, or `[r,g,b]`.
- **Rails** are the power buses (top/bottom lines). Connect power/ground to a
  rail, not with long wires: `["rail","GND"]`.
- **Ports have a facing.** e.g. an `led` `anode` defaults to `"N"`; if the LED is
  driven from a pin to its *left*, pass `"args": {"anode": "W"}` so the wire
  enters straight. `wirewright components` shows each type's tunable facings.

## Common fixes (DRC failures are usually modelling bugs)

- **`coincident-wires`** between two nets that share a pin → they are the *same*
  electrical node. Merge into **one** net with all terminals:
  `nodes: [["port","U1","D7"], ["port","BTN","pin"], ["port","PD","a"]]`.
- **`unconnected-pin`** → a component has a port you named but the net doesn't
  actually include it, or the id/port is misspelled.
- **`wire-over-component`** → give components more room (bump their `x`/`y`
  apart); the router needs a channel. Widening `canvas.w`/`h` helps.
- **`wires-too-close`** → same: spread components, or lower the DRC via
  `"config": {"min_wire_spacing": 8}` (only if you truly want them tight).

## Layout tips for clean results

- Put the MCU/hub in the middle, inputs left, outputs/indicators right.
- Give each component its own horizontal band; leave ~150–250 px between a
  component column and the next so wires have a channel.
- Two-terminal parts (resistor, LED) in series → model them as real components
  with two nets, e.g. `pin → R.a` and `R.b → GND`. The DRC then proves the
  resistor is connected.
- Prefer rails for `5V`/`GND` over point-to-point power wires.

## Config knobs (optional `"config"` block or CLI flags)

`pitch` (grid px), `bend_penalty` (higher = straighter), `min_wire_spacing`,
`body_clearance`, `label_soft_cost`, `stub_px`. Defaults are good; only touch
them for dense boards.

See `docs/contract-format.md` for the exhaustive field reference and
`examples/json/` for working contracts.
