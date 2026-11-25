# AdeptBT — JLCPCB assembly BOM

Owner for PCBA quotes. Generated from schematic `hardware/adeptbt.kicad_sch` (rev on board **3.10**).

**Upload file:** [`JLCPCB_ASSEMBLY_BOM.csv`](JLCPCB_ASSEMBLY_BOM.csv)  
**CPL (positions):** `hardware/exports/adeptbt_cpl.csv`  
**Gerbers:** `hardware/gerbers/` (ZIP for PCB + paste)

Prefer LCSC / JLCPCB assembly. **Verify live stock and LCSC codes before order.** Blank `LCSC Part #` means not locked — pick in the JLC BOM tool (Basic passives) or search Extended.

## Quote package

1. Gerber ZIP (4-layer) from `hardware/gerbers/`.
2. `docs/JLCPCB_ASSEMBLY_BOM.csv`.
3. `hardware/exports/adeptbt_cpl.csv` (mm, both sides).
4. Order: **Standard PCBA** + **X-ray** (Raytac + TMC2209 QFN).

## Locked LCSC (do not substitute without a decision)

| Designator | MPN | LCSC | Notes |
|------------|-----|------|-------|
| U1 | MDBT50Q-1MV2 | **C5118826** | Extended; Standard + X-ray |
| U2, U3 | TMC2209-LA | **C465949** | Extended; X-ray |
| U4 | AP63205WU-7 | **C2071056** | Extended |
| U5 | MCP73871 | **C5121473** | Extended |
| U6 | AMS1117-3.3 | **C6186** | Basic |
| Q2, Q3 | MMBT2222A | **C8512** | Basic |
| D2, D3 | 1N4148W | **C81598** | Basic |
| J_STEP1, J_STEP2, J_PWR1 | TE 2383941-6 | **C3816695** | SMD 3.81 mm 7 A |

## Must search at order (SMT, no locked LCSC yet)

| Designator | Need |
|------------|------|
| D1 | SMBJ24A (SMB) |
| Q1 | AO3407-class P-FET SOT-23 ≥40 V |
| F1 | PPTC ~2 A hold, 1812 |
| L1 | 4.7 µH, 6.3×6.3 |
| J_USB1 | GCT USB4105-xx-A mid-mount (or LCSC equiv) |
| J_BAT1 | JST-PH 2P SMD (DNP OK wall-wart SKU) |
| RSA1/2, RSB1/2 | 0.12 Ω 1206 sense (**schematic value**; older notes said 0.11) |
| All ceramics / LEDs / 1k / 5.1k / 2k / 10k | Match value + package in JLC Basic |

## THT / hand-solder (exclude from SMT or after-SMT)

| Designator | Part |
|------------|------|
| J_DC1 | 5.5×2.1 barrel (doc candidate C2880552 / PJ-063AH) |
| J_AN1, J_DG1, J_SWD1 | 2.54 mm headers |
| JP_V+1, JP_VM1, JP_VM2 | 2.54 mm jumpers |
| M1–M4 | M2 holes — mechanical only |

## Locked decisions

| Decision | Choice |
|----------|--------|
| Screw current | **7 A** TE 2383941-6 |
| Charger | **MCP73871** (not TP4056) |
| VIN max | **18 V** → **SMBJ24A** |
| DC inlet | **5.5×2.1** on `VIN_RAW` parallel with screw |

## Film-scanner / wall-wart

- 12–18 V → barrel and/or screw → protect → VIN → VM + buck.
- Optional DNP: `J_BAT1`, `U5`, related charger caps for wart-only SKUs.

## Regen

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export bom \
  --fields "Reference,Value,Footprint,QUANTITY,DNP" \
  --group-by "Value,Footprint" --exclude-dnp \
  -o hardware/exports/bom_from_sch.csv hardware/adeptbt.kicad_sch
# Then re-run the assembly CSV builder / edit locks in this doc.
```
