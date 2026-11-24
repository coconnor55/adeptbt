# AdeptBT — JLCPCB-first BOM (rev 0.5 target)

Prefer LCSC / JLCPCB assembly. Verify live stock before order.

## Locked majors

| Role | MPN | JLCPCB / LCSC | Notes |
|------|-----|---------------|-------|
| BLE MCU | Raytac **MDBT50Q-1MV2** | **C5118826** | Extended; **Standard PCBA** + X-ray |
| Stepper ×2 | **TMC2209-LA** | **C465949** | QFN-28; X-ray |
| Screw ×3 | TE **2383941-6** | **C3816695** | SMD 3.81 mm **7 A** |
| Charger | **MCP73871** | **C5121473** | Extended; locked (not TP4056) |
| Buck | **AP63205WU-7** | **C2071056** | Extended; Vin to 32 V |
| LDO 3.3 V | **AMS1117-3.3** | **C6186** | Basic |
| TVS | **SMBJ24A** | search LCSC | **24 V class** — VIN to 18 V (auto) |
| NPN ×2 | **MMBT2222A** | **C8512** | Basic |
| Flyback ×2 | **1N4148W** | **C81598** | Basic |
| Barrel 5.5×2.1 | CUI PJ-063AH / Würth 694106106102 / LCSC equiv | Ext | On `VIN_RAW`; see below |

## Locked decisions

| Decision | Choice |
|----------|--------|
| Screw current | **7 A** TE 2383941-6 |
| Charger | **MCP73871** (JLCPCB Extended) — better power-path than TP4056 |
| VIN max | **18 V** → **SMBJ24A** (not 18 A) |
| DC inlet | **5.5 mm OD × 2.1 mm ID** barrel in parallel with screw VIN |

## Power path (on-board, JLCPCB)

| Role | Preferred | LCSC | Class |
|------|-----------|------|-------|
| Buck | AP63205WU-7 | C2071056 | Ext |
| LDO | AMS1117-3.3 | C6186 | Basic |
| Charger | **MCP73871** | C5121473 | Ext |
| P-FET reverse | AO3407-class ≥40 V | search | Ext |
| TVS | **SMBJ24A** | search | Ext |
| PPTC ~2 A | 1812 | search | Ext |
| Barrel | 5.5×2.1 SMT or THT | C2880552 / PJ-063AH / WE | Ext (THT often hand-solder) |
| BAT JST | PH 2P SMD | LCSC | Ext — DNP OK for wart-only |

## Film-scanner / wall-wart

- 12 V (or up to 18 V) → barrel and/or screw `VIN_RAW` → protect → `VIN` → VM + buck.
- Battery/charger BOM delta is small; keep on PCB, DNP for scanner SKUs if desired.

## Assembly

- **Standard PCBA** (Raytac) + X-ray for Raytac + TMC.
- TE screws SMT; barrel may be THT hand-solder depending on chosen footprint.
