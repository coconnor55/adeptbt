# AdeptBT hardware (rev 0.2)

KiCad 10 project from the locked AdeptBT spec. Footprints are real KiCad library parts (copied under `libs/AdeptBT.pretty`).

| File | Purpose |
|------|---------|
| `adeptbt.kicad_pro` | Project |
| `adeptbt.kicad_sch` | Functional schematic (block-level; complete symbol wiring next) |
| `adeptbt.kicad_pcb` | Outline, placement, silkscreen with real footprints |
| `exports/` | `adeptbt_pcb.svg`, `adeptbt_schematic.pdf` |
| `gerbers/` | Preliminary Gerbers + drill (placement only — not fab-ready) |
| `libs/AdeptBT.pretty/` | Raytac MDBT50Q, QFN-28, USB-C, JST-PH, MKDS-1-6, headers, M2 |
| `silkscreen_preview.svg` | Quick silk layout preview |
| `../tools/gen_adeptbt_pcb.py` | Regenerator |

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
