# AdeptBT — 4-layer stackup

Board: 85.6 × 53.98 mm, 1.6 mm thick (JLCPCB 4-layer default OK).

| Layer | Name | Role |
|-------|------|------|
| L1 | `F.Cu` | Signals + GND pour (thermal relief) |
| L2 | `In1.Cu` | **Solid GND** |
| L3 | `In2.Cu` | **Solid GND** (heavy return; split for +3V3/+5V later if needed) |
| L4 | `B.Cu` | Signals + GND pour (thermal relief) |

## Rules

- Prefer short vias from decoupling GND pads into the inner GND planes.
- No copper in the U1 antenna keepout (south of module, toward the bottom edge).
- Fill zones after placement changes: `python3 tools/pour_gnd.py` (uses KiCad’s Python / `pcbnew`).
- Full signal routing is separate; this step is planes + stitch vias only.

## Owner

`hardware/adeptbt.kicad_pcb` (pcbnew placement) → `tools/pour_gnd.py` (nets, zones, vias, fill). `tools/gen_adeptbt_pcb.py` is stopped and must not overwrite the board.
