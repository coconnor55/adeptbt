# AdeptBT hardware (rev 0.1)

KiCad 8+ project generated from the locked AdeptBT spec.

| File | Purpose |
|------|---------|
| `adeptbt.kicad_pro` | Project |
| `adeptbt.kicad_sch` | Functional schematic (block-level; complete symbol wiring in KiCad) |
| `adeptbt.kicad_pcb` | Board outline, placement, silkscreen, connector pads |
| `silkscreen_preview.svg` | Quick silk layout preview |
| `../docs/DESIGN.md` | Locked design |
| `../docs/BOM.md` | Preliminary BOM |
| `../tools/gen_adeptbt_pcb.py` | Regenerator for placement/silk |

## Layout (credit card 85.6 × 53.98 mm)

- **Top long edge:** `J_STEP1` / `J_STEP2` — `A1 A2 B1 B2 VM GND`
- **Bottom long edge:** `J_PWR` — `VIN GND V+ OUT1 V+ OUT2`
- **Left short edge:** USB-C
- **Right:** analog + digital headers
- **Center:** U1 MDBT50Q, U2/U3 TMC2209, BAT JST, SWD
- **Corners:** M2 holes

## Before fab (required)

1. Open in **KiCad 8+**.
2. Replace placeholder footprints with vendor drawings (Raytac MDBT50Q, Phoenix MKDS 1/6 SMD, USB-C, TMC2209 QFN-28).
3. Complete schematic symbols and associate footprints; annotate.
4. Route nets; pour GND on inner/bottom; run DRC.
5. Plot Gerbers + drill into `gerbers/`.

Regenerate placement baseline:

```bash
python3 tools/gen_adeptbt_pcb.py
```
