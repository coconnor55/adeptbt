# AdeptBT — preliminary BOM

Exact LCSC/DigiKey PNs locked at fab time; functional list:

| Ref | Qty | Description |
|-----|-----|-------------|
| U1 | 1 | Raytac MDBT50Q-1MV2 |
| U2 U3 | 2 | TMC2209-LA (QFN28) |
| U4 | 1 | Buck VIN→5V (e.g. AP63205 class, Vin≥18–24V) |
| U5 | 1 | LiPo charger ~500 mA (e.g. MCP73871 / BQ25185 class) |
| U6 | 1 | 3.3 V LDO ≥300 mA (e.g. AP2112-3.3) |
| Q1 | 1 | P-FET ≥40 V reverse protect |
| Q2 Q3 | 2 | 2N2222A (SOT-23 ok) |
| D1 | 1 | TVS SMBJ18A/24A on VIN |
| D2 D3 | 2 | Flyback 1N4148/1N4007 on outs |
| F1 | 1 | PPTC ~2 A hold on VIN |
| J_USB | 1 | USB-C receptacle (16-pin mid-mount or equivalent) |
| J_BAT | 1 | JST-PH 2.0 2-pin SMD |
| J_STEP1 J_STEP2 J_PWR | 3 | 6-pos screw 3.81 mm SMD |
| J_AN J_DG J_SWD | 3 | Pin headers 2.54 mm |
| JP_* | — | 2.54 mm jumpers: V+, VM×2, AIN dividers×4 |
| LED1-3 | 3 | Power / charge / user |
| R/C | — | Sense R for TMC, dividers, USB CC, decoupling |

Assembly: JLCPCB SMT where possible; hand-solder module/terminals if needed.
