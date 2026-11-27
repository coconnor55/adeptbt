# AdeptBT hardware (rev 2.0)

KiCad 10 project — JLCPCB-first. Schematic: `tools/gen_adeptbt_sch.py` if needed. **PCB placement is owned by pcbnew** (`adeptbt.kicad_pcb`). Do not run `tools/gen_adeptbt_pcb.py` — it refuses to write.

| File | Purpose |
|------|---------|
| `adeptbt.kicad_pro` | Project |
| `adeptbt.kicad_sch` | Wired schematic (global labels + GPIO lock) |
| `adeptbt.kicad_pcb` | Board (edit in KiCad; source of truth for placement) |
| `fp-lib-table` / `sym-lib-table` | AdeptBT + jlc libraries |
| `libs/AdeptBT.pretty/` | TE 3.81 mm screw, barrel 5.5×2.1, USB-C, JST, headers, M2 |
| `libs/jlc/` | Raytac MDBT50Q + TMC2209 symbols/footprints (LCSC) |
| `exports/` | SVG / PDF / ERC JSON |
| `../docs/JLCPCB_BOM.md` | LCSC SKUs + keep/reconsider |
| `../docs/NETLIST.md` | Nets + GPIO lock |

## Layout (85.6 × 53.98 mm)

- **Top:** `J_STEP1` / `J_STEP2` — TE 2383941-6; may slide laterally
- **Bottom:** `J_DC` + `J_BAT` (beside DC) + `J_PWR`; may slide laterally
- **Left:** USB-C — pads/silk/fab on-board; label on the board side
- **Right:** `J_AN` / `J_DG`; U1 antenna keepout faces this edge (angle 90°)
- **Center:** U2/U3 TMC2209, `J_SWD` west of U1, `JP_V+` (1×3), `JP_VM1`/`JP_VM2` (1×2). No JP_AIN.
- **Silk rule:** no labels past Edge.Cuts. Check: `python3 tools/check_silk.py`
- **Stackup:** 4-layer — `In1`/`In2` solid GND. After placement changes in pcbnew: KiCad Python `tools/pour_gnd.py` (see `docs/STACKUP.md`)
- **TMC neighborhood:** KiCad Python `tools/route_tmc_local.py` (short locked stubs + EP vias). Then `tools/freeroute_rest.sh` for the rest (ignore GND).

## JLCPCB (rev 0.4)

- Raytac **C5118826** + TMC **C465949** → Standard + X-ray
- Screws **C3816695** (7 A); charger **MCP73871** **C5121473**; TVS **SMBJ24A** (VIN≤18 V)
- Next: wire power discretes, sense Rs, GND pour, DRC, Gerbers
