# AdeptBT — preliminary BOM

**PCBA quote owner:** [`JLCPCB_BOM.md`](JLCPCB_BOM.md) + [`JLCPCB_ASSEMBLY_BOM.csv`](JLCPCB_ASSEMBLY_BOM.csv).

Exact LCSC/DigiKey PNs locked at fab time; functional list:

| Ref | Qty | Description |
|-----|-----|-------------|
| U1 | 1 | Raytac MDBT50Q-1MV2 |
| U2 U3 | 2 | TMC2209-LA (QFN28) |
| U4 | 1 | **AP63205WU-7** buck VIN→5V — **C2071056** |
| U5 | 1 | **MCP73871** LiPo charger (~500 mA) — **C5121473** |
| U6 | 1 | AMS1117-3.3 LDO — **C6186** |
| L1 | 1 | 4.7 µH buck inductor (6.3×6.3) |
| Q1 | 1 | P-FET ≥40 V reverse protect (AO3407-class) |
| Q2 Q3 | 2 | MMBT2222A SOT-23 — **C8512** |
| D1 | 1 | TVS **SMBJ24A** on VIN (18 V max) |
| D2 D3 | 2 | 1N4148W flyback — **C81598** |
| F1 | 1 | PPTC ~2 A hold on VIN (1812) |
| RSA1 RSB1 RSA2 RSB2 | 4 | **0.10 Ω** sense (1206) — **C346768** |
| RPROG1 | 1 | 2 kΩ MCP73871 PROG1 (~500 mA) |
| J_USB | 1 | USB-C receptacle (16-pin mid-mount or equivalent) |
| J_BAT | 1 | JST-PH 2.0 2-pin SMD |
| J_STEP1 J_STEP2 J_PWR | 3 | TE 2383941-6 SMD 3.81 mm 7 A (**C3816695**) |
| J_DC | 1 | **C84007** HRO DC-005C-20A (3 A, 5.5×2.0 mate) on `VIN_RAW` — PCB footprint swap pending |
| J_AN J_DG J_SWD | 3 | Pin headers 2.54 mm (LCSC **C6332200** / **C37208** / **C6332198**) |
| JP_V+ | 1 | 2.54 mm 1×3 (**C49257**) |
| JP_VM1 JP_VM2 | 2 | 2.54 mm 1×2 (**C492401**) |
| Shunts | 3 | 2.54 mm 2-pin capped (**C100114**) — V+ + VM1 + VM2 |
| PWR1 CHG1 USR1 | 3 | Power / charge / user LEDs (0603) |
| R4 R5 R6 | 3 | LED series 1k (0603) |
| C1–C31, C40–C42, C50–C51, C60–C61 | — | Decoupling — see [`docs/DECOUPLING.md`](DECOUPLING.md) |
| R2 R3 + USB CC | — | Base 1k; USB CC as required |

Assembly: JLCPCB SMT where possible; hand-solder module/terminals if needed.
