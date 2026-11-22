# AdeptBT hardware (rev 0.4)

KiCad 10 project — JLCPCB-first. Regenerate with `tools/gen_adeptbt_sch.py` and `tools/gen_adeptbt_pcb.py`.

| File | Purpose |
|------|---------|
| `adeptbt.kicad_pro` | Project |
| `adeptbt.kicad_sch` | Wired schematic (global labels + GPIO lock) |
| `adeptbt.kicad_pcb` | Outline, placement, silk (TE + JLC footprints) |
| `fp-lib-table` / `sym-lib-table` | AdeptBT + jlc libraries |
| `libs/AdeptBT.pretty/` | TE 3.81 mm screw, barrel 5.5×2.1, USB-C, JST, headers, M2 |
| `libs/jlc/` | Raytac MDBT50Q + TMC2209 symbols/footprints (LCSC) |
| `exports/` | SVG / PDF / ERC JSON |
| `../docs/JLCPCB_BOM.md` | LCSC SKUs + keep/reconsider |
| `../docs/NETLIST.md` | Nets + GPIO lock |

## Layout (85.6 × 53.98 mm)

- **Top:** `J_STEP1` / `J_STEP2` — TE 2383941-6 (`A1 A2 B1 B2 VM GND`)
- **Bottom:** `J_DC` 5.5×2.1 barrel + `J_PWR` TE (`VIN GND V+ OUT1 V+ OUT2`)
- **Left:** USB-C
- **Right:** analog + digital headers
- **Center:** U1 MDBT50Q, U2/U3 TMC2209, BAT, SWD

## JLCPCB (rev 0.4)

- Raytac **C5118826** + TMC **C465949** → Standard + X-ray
- Screws **C3816695** (7 A); charger **MCP73871** **C5121473**; TVS **SMBJ24A** (VIN≤18 V)
- Next: wire power discretes, sense Rs, GND pour, DRC, Gerbers
