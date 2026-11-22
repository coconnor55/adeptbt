# AdeptBT — preliminary BOM

Exact LCSC/DigiKey PNs locked at fab time; functional list:

| Ref | Qty | Description |
|-----|-----|-------------|
| U1 | 1 | Raytac MDBT50Q-1MV2 |
| U2 U3 | 2 | TMC2209-LA (QFN28) |
| U4 | 1 | Buck VIN→5V (e.g. AP63205 class, Vin≥18–24V) |
| U5 | 1 | **MCP73871** LiPo charger (~500 mA) — JLCPCB **C5121473** |
| U6 | 1 | AMS1117-3.3 LDO — **C6186** |
| Q1 | 1 | P-FET ≥40 V reverse protect (AO3407-class) |
| Q2 Q3 | 2 | MMBT2222A SOT-23 — **C8512** |
| D1 | 1 | TVS **SMBJ24A** on VIN (18 V max) |
| D2 D3 | 2 | 1N4148W flyback — **C81598** |
| F1 | 1 | PPTC ~2 A hold on VIN |
| J_USB | 1 | USB-C receptacle (16-pin mid-mount or equivalent) |
| J_BAT | 1 | JST-PH 2.0 2-pin SMD |
| J_STEP1 J_STEP2 J_PWR | 3 | TE 2383941-6 SMD 3.81 mm 7 A (**C3816695**) |
| J_DC | 1 | **5.5×2.1** barrel on `VIN_RAW` (CUI PJ-063AH / Würth / LCSC) |
| J_AN J_DG J_SWD | 3 | Pin headers 2.54 mm |
| JP_* | — | 2.54 mm jumpers: V+, VM×2, AIN dividers×4 |
| LED1-3 | 3 | Power / charge / user |
| R/C | — | Sense R for TMC, dividers, USB CC, decoupling |

Assembly: JLCPCB SMT where possible; hand-solder module/terminals if needed.
