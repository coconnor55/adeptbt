# Part locks (JLCPCB)

Canonical SKU table: `docs/JLCPCB_BOM.md`. This note is **why**, not a second BOM.

2026-11-22. **JLCPCB-first.** Prefer LCSC parts that PCBA can place.

| Decision | Choice | Why / rejected |
| --- | --- | --- |
| MCU | Raytac MDBT50Q-1MV2 C5118826 | Keep; forces Standard + X-ray — no good drop-in |
| Drivers | TMC2209-LA C465949 ×2 | Keep; **LA-T C2150710** OK at JLC (same QFN; tape/reel only) |
| Screws ×3 | TE **2383941-6** C3816695 (7 A) | Phoenix MKDS THT costly for PCBA; **12 A 2383945-6 rejected** — 7 A enough |
| Charger | **MCP73871** C5121473 | Locked. TP4056 is cheaper/Basic but needs extra protect; MCP73871 is Extended with better power-path |
| Buck | AP63205WU-7 C2071056 | Vin to 32 V covers 12–18 V |
| LDO | AMS1117-3.3 C6186 | Basic |
| TVS | **SMBJ24A** | VIN ≤18 V (auto) — not SMBJ18A |
| Barrel | **C84007** HRO DC-005C-20A (3 A, 5.5×2.0 mate) | Locked 2026-11-25. Tip=`VIN_RAW`, sleeve+switch=`GND`. Footprint `BarrelJack_HRO_DC-005C-20A_Horizontal`. **C55072354** 10 A rejected |
| Outs | MMBT2222A C8512 + 1N4148W C81598 | Basic |

2026-11-24. Locked passives/connectors from JLC quote after rejecting bad auto-matches (01005 for C1…, THT for RSA, ADUM for J_DG1). Full table: `docs/JLCPCB_BOM.md`. LEDs provisional **C2286** red.

2026-11-25. Sense locked **0.10 Ω** 1206 **C346768** (CSR1206FKR100, ±1%, 0.5 W). Replaces **C858775** 0.12 Ω. ~1.92 A RMS at VREF=2.5 V; ~0.4 W at 2 A RMS (0.5 W part — usable, not generous; prefer 1 W 1206 when stocked).

Footprint file `TE_2383945-6_…` is **geometry only** (same 3.81 mm pitch); silkscreen/value is **2383941-6**.

2026-11-25. Male headers locked for JLC wave (Extended, high stock): **C492401** 1×2 (JP_VM×2), **C49257** 1×3 (JP_V+), **C6332198** 1×5 (SWD), **C37208** 1×6 (DG), **C6332200** 1×7 (AN).

2026-11-25. Barrel locked **C84007** (DC-005C-20A). Footprint `AdeptBT:BarrelJack_HRO_DC-005C-20A_Horizontal` on `J_DC1` (PCB **3.62**); tip=`VIN_RAW`, sleeve+switch=`GND`.

2026-11-25. Jumper shunts ×3: BOOMELE capped **C100114** (JP_V+ + JP_VM1 + JP_VM2). Only three jumper sites on the board; accessory (not CPL).
