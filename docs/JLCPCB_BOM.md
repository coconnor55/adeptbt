# AdeptBT — JLCPCB assembly BOM

Owner for PCBA quotes. Generated from schematic `hardware/adeptbt.kicad_sch` (rev on board **3.10**).

**Upload file:** [`JLCPCB_ASSEMBLY_BOM.csv`](JLCPCB_ASSEMBLY_BOM.csv)  
**CPL (positions):** [`JLCPCB_CPL.csv`](JLCPCB_CPL.csv) (same as `hardware/exports/adeptbt_cpl.csv`)  
**Gerbers:** `hardware/gerbers/` (ZIP for PCB + paste)

### CPL format (JLCPCB)

KiCad’s raw pos CSV (`Ref,PosX,PosY,Rot,Side`) is **rejected**. Use columns:

`Designator,Mid X,Mid Y,Layer,Rotation`

with `Top`/`Bottom`, millimetres (optional `mm` suffix), positive coordinates.

Prefer LCSC / JLCPCB assembly. **Verify live stock and LCSC codes before order.** Blank `LCSC Part #` means THT hand-solder or not locked.

## Quote package

1. Gerber ZIP (4-layer) from `hardware/gerbers/`.
2. `docs/JLCPCB_ASSEMBLY_BOM.csv`.
3. `docs/JLCPCB_CPL.csv` (or `hardware/exports/adeptbt_cpl.csv`).
4. Order: **Standard PCBA** + **X-ray** (Raytac + TMC2209 QFN).

## Locked LCSC (do not substitute without a decision)

| Designator | MPN | LCSC | Notes |
|------------|-----|------|-------|
| U1 | MDBT50Q-1MV2 | **C5118826** | Extended; Standard + X-ray; watch shortfall |
| U2, U3 | TMC2209-LA | **C465949** | Extended; X-ray; watch shortfall |
| U4 | AP63205WU-7 | **C2071056** | Extended |
| U5 | MCP73871 | **C5121473** | Extended |
| U6 | AMS1117-3.3 | **C6186** | Basic |
| Q1 | AO3407 | **C22751455** | Extended |
| Q2, Q3 | MMBT2222A | **C8512** | Basic |
| D1 | SMBJ24A | **C5178956** | Extended |
| D2, D3 | 1N4148W | **C81598** | Basic |
| L1 | LQH66SN4R7M03L | **C703091** | Extended |
| F1 | SMD1812-200C-30V | **C2760293** | Extended 2 A hold |
| J_USB1 | USB4105-GF-A | **C3020560** | Extended |
| J_BAT1 | S2B-PH-SM4-TB | **C295747** | Extended; DNP OK wart SKU |
| J_STEP1/2, J_PWR1 | TE 2383941-6 | **C3816695** | SMD 3.81 mm 7 A; watch shortfall |
| C1… (100n 0402) | CL05B104KO5NNNC | **C1525** | Basic — not 01005 |
| C2 | CL10A105KB8NNNC | **C15849** | Basic |
| C10, C20 | CL10B223KB8NNNC | **C21122** | Basic |
| C4, C40, C50 | CL21A106KAYNNNE | **C15850** | Basic |
| C12, C22, C60, C61 | CL21A475KAQNNNE | **C1779** | Basic |
| C41, C51, C412 | CL21A226MAQNNNE | **C45783** | Basic |
| C15, C25, C31 | RST100UF25V004 | **C4747964** | Extended SMD elec |
| R2–R6 | 1k 0603 | **C21190** | Basic |
| RCC1/2 | 5.1k 0603 | **C23186** | Basic |
| RPROG1 | 2k 0603 | **C22975** | Basic |
| RVREF1/2 | 10k 0603 | **C25804** | Basic |
| RSA/RSB | PT1206FR-7W0R12L | **C858775** | Extended SMD 0.12 Ω — not THT |
| PWR1, CHG1, USR1 | KT-0603R | **C2286** | Basic red; recolor at order OK |

## Rejected auto-matches (do not re-accept)

| Designator | Bad match | Why |
|------------|-----------|-----|
| C1… 100n | C161362 (01005) | Footprint is **0402** |
| RSA/RSB | C714389 (THT MOF) | Footprint is **1206 SMD** |
| J_DG1 | C33845697 (ADUM340 isolator) | Part is a **1×06 header**; Comment “DIGITAL” poisoned match |

## THT / hand-solder (blank LCSC)

| Designator | Part |
|------------|------|
| J_DC1 | 5.5×2.1 barrel (SEARCH at order; candidate C2880552) |
| J_AN1, J_DG1, J_SWD1 | 2.54 mm headers |
| JP_V+1, JP_VM1, JP_VM2 | 2.54 mm jumpers |
| M1–M4 | M2 holes — mechanical only (omit from assembly BOM) |

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
