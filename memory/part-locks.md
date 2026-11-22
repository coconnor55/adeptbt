# Part locks (JLCPCB)

Canonical SKU table: `docs/JLCPCB_BOM.md`. This note is **why**, not a second BOM.

2026-11-22. **JLCPCB-first.** Prefer LCSC parts that PCBA can place.

| Decision | Choice | Why / rejected |
| --- | --- | --- |
| MCU | Raytac MDBT50Q-1MV2 C5118826 | Keep; forces Standard + X-ray — no good drop-in |
| Drivers | TMC2209-LA C465949 ×2 | Keep; on LCSC |
| Screws ×3 | TE **2383941-6** C3816695 (7 A) | Phoenix MKDS THT costly for PCBA; **12 A 2383945-6 rejected** — 7 A enough |
| Charger | **MCP73871** C5121473 | Locked. TP4056 is cheaper/Basic but needs extra protect; MCP73871 is Extended with better power-path |
| Buck | AP63205WU-7 C2071056 | Vin to 32 V covers 12–18 V |
| LDO | AMS1117-3.3 C6186 | Basic |
| TVS | **SMBJ24A** | VIN ≤18 V (auto) — not SMBJ18A |
| Barrel | 5.5×2.1 (CUI PJ-063AH footprint in lib; LCSC equiv at order) | Not 5.3 mm; tip=`VIN_RAW`, sleeve=`GND` |
| Outs | MMBT2222A C8512 + 1N4148W C81598 | Basic |

Footprint file `TE_2383945-6_…` is **geometry only** (same 3.81 mm pitch); silkscreen/value is **2383941-6**.
