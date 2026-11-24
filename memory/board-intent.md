# Board intent & product

2026-11-22. AdeptBT is a credit-card nRF52840 control board (Raytac MDBT50Q-1MV2), dual TMC2209, dual low-side outs, USB-C + LiPo + VIN. Spec lives in `docs/DESIGN.md` / `docs/NETLIST.md`.

**First commercial use:** [film-scanner-120](https://github.com/coconnor55/film-scanner-120) (or local `Documents/GitHub/film-scanner-120`). That product runs **two steppers + board from one 12 V wall wart**. Motor VM and logic share VIN via jumpers/buck — not a separate Xiao + breakout stack.

Battery + MCP73871 + JST stay on the PCB even when unused: BOM delta is negligible; leave those parts **DNP** on scanner SKUs if desired. Same board serves portable / LiPo builds later.

VIN may go to **18 V** (auto). Wall-wart inlet is **5.5×2.1 mm** barrel (`J_DC`) in parallel with screw `VIN_RAW`.

Related EcoSpring / pump work was a prior chat seed; AdeptBT is the shared motion+I/O board, not EcoSpring-specific.

**Silk (2026-11-22, rev 0.5):** Connector pin names are one label per pad (not a grouped string). Owner: `tools/gen_adeptbt_pcb.py` → `silk_at_pads`.

**Layout (2026-11-22, rev 0.6):** J_USB origin at x=3.1 (PCB Edge mark); J_SWD on bottom edge at (30, H-2.5); connector silk outside outline+2mm.

**Layout (2026-11-22, rev 0.7):** M1–4 silk hidden (formerly misnamed H1–4); J_USB at x=5; J_AN/J_DG between M2–M4; brand “Adept BT” + v1 under U1; J_BAT silk is +/- only.

**Layout (2026-11-22, rev 1.1):** J_SWD between STEP1/2; J_BAT bottom-right; J_USB at x=7; JP_* are silk legends only (no footprints yet). Silk check: `tools/check_silk.py`.

**Layout (2026-11-22, rev 1.5):** J_USB inset on-board; J_SWD near U1; J_BAT bottom-right left of DG with +/- beside pads (outside silk); STEP/PWR inset; AN/DG pin offsets glyph-aware; JP_* legends clear of J_DC fab. `check_silk.py` must score text×pads, text×F.SilkS/F.Fab, and footprint silk/fab off Edge.Cuts — text-only is a false clean.

**Layout rules (2026-11-22, rev 1.6) — placement freedom until routing forces a change:**
- No silk **labels** past Edge.Cuts (glyph bbox). Connector body may overhang only where named.
- **J_USB:** left edge; may slide up/down; pads + F.SilkS + F.Fab must stay on-board (origin ≈4.1). Label on the board side (right of pads). No overhang allowlist — `check_silk.py` also fails pad past Edge.Cuts.
- **J_STEP1 / J_STEP2:** top edge; may slide laterally.
- **J_AN / J_DG:** right edge; may slide up/down slightly; keep clearance to corner screw holes.
- **J_DC / J_PWR / J_BAT:** bottom edge; may slide laterally.
- **J_SWD** and jumpers: anywhere silk fits.
- Prefer low noise: keep motor drivers near stepper connectors; keep analog away from stepper/VM switching when sliding AN/DG.

**Layout (2026-11-22, rev 1.8) — A/B hybrid:**
- U1 at (62,28) **90°** — antenna keepout toward AN/DG; `J_SWD` west of U1.
- `J_BAT` beside `J_DC` on bottom; `J_PWR` shifted right.
- Jumpers placed: `JP_V+` 1×3 (3V3/V+/VIN), `JP_VM1`/`JP_VM2` 1×2 (VIN/EXT). **No JP_AIN** — AIN is 3.3 V direct; external divider if needed.
- V+ select is 3V3 or VIN only (no 5V option).

**Decoupling (2026-11-22, rev 1.9):** Caps on sch + PCB per `docs/DECOUPLING.md` (TMC CP/VS/5VOUT, U1 3V3, USB, VIN). Buck/LDO/charger caps deferred until those footprints land.

**Planes (2026-11-22, rev 2.0):** 4-layer heavy GND — `In1.Cu` + `In2.Cu` solid GND; F/B pours with thermals; stitch vias. Owner: `docs/STACKUP.md`, `tools/pour_gnd.py`.

**Floorplan (2026-11-23, rev 2.4):** Power upper-left (jack, protect, buck/LDO/charger, `JP_V+`); MCU lower-left with antenna tip flush **south**; steppers right (`J_STEP1`/`J_STEP2`); `J_PWR`/`J_BAT` top; `J_DC`/`J_USB` left on-board (shell at edge). AN/DG west of STEP courtyards (x≲60). Pin silk **1.25 mm**. `check_silk.py` must pass silk **and** F.CrtYd body×body.

**Floorplan (2026-11-23, rev 2.5):** Screenshot arrows applied — `J_DC` on-board left; `U1` flush lower-left; SWD left toward MCU; STEP centers at x=70 clear of H2/H4; mid headers spaced. `JP_VM*` horizontal @90° with labels south. Brand mid-east. `check_silk` silk+body+pad×pad clean; `pour_gnd` run.

**Floorplan (2026-11-23, rev 2.6):** 1 mm F.Fab outline keep-away (`BODY_CLEAR_MM`); 6×6 mm square F.SilkS keepouts on H1–H4; STEP at x=66 clear of hole keepouts; U1 at (13,44.5); AN/DG pin silk east of headers; `JP_VM*` vertical on south edge (no horizontal slot vs STEP2). `check_silk` silk+body clean; GND poured; gerbers refreshed.

**Floorplan (2026-11-23, rev 2.7):** `J_BAT` at (56,18) @180° next to STEP1/barrel power lane; AN silk west / DG silk east; U6 west of DG (CrtYd↔DG Fab ≥3 mm); U6/L1 clear of DG. `J_USB` stays @90° (PCB Edge local +Y → left). `check_silk` silk+body clean; GND poured; gerbers refreshed.

**Floorplan (2026-11-23, rev 2.8):** `J_BAT` at (28,18) @0° east of barrel / west of STEP1 — plug opens south for mating clearance. AN/DG silk east; `JP_V+` at (38,14). `check_silk` silk+body clean; GND poured; gerbers refreshed.

**Floorplan (2026-11-23, rev 2.9):** Hand `J_USB` @−90° (PCB Edge outboard) at (5,28). PWR1/CHG1/USR1 + R4–R6 left edge under USB west of U1. OUT drivers Q2/Q3/R2/R3/D2/D3 column at x=63.5 between RSA and U2/U3. All sch parts on board (70 footprints). `check_silk` silk+body clean; GND poured; gerbers refreshed.

**Silk (2026-11-23, rev 2.10):** Board rev as two F.SilkS lines (`rev` / `2.10`) above H4 at (81.5, 44)/(81.5, 45.5). `check_silk` clean.

**Placement source (2026-11-23, rev 2.15):** `hardware/adeptbt.kicad_pcb` is owned by pcbnew. `tools/gen_adeptbt_pcb.py` is **stopped** (refuses to write). Snapshot: `hardware/snapshots/pcbnew-2026-11-23.kicad_pcb`. Sch rev 0.6 loads in KiCad 10 (unit prefixes fixed). Nets on PCB from `tools/apply_sch_netlist.py` (or Tools → Update PCB from Schematic). J_USB uses `AdeptBT:USB_C_GCT_16P` so pin numbers match the GCT footprint.

**Version (2026-11-24, rev 3.10):** PCB `title_block` rev and B.SilkS `AdeptBT rev 3.10` (mirrored, one string) are the version owner. JLCPCB does not surcharge bottom silkscreen when `.GBO` is in the Gerber set. Status LEDs are `PWR1`/`CHG1`/`USR1`. Do not rewrite rev downward; bump z only on later ship. pcbnew owns the board file. Antenna keepout is y≥50.0 with **copperpour not_allowed**. QFN-28 pads are 0.24×0.85. Freerouting ignores GND — add explicit **GND stitch vias** after import (islands at C41/C2/USB need in-island vias). Snapshot: `hardware/snapshots/fab-crowd-stitch-3.10.kicad_pcb`.

**Routing (2026-11-24, rev 3.2):** Freerouting JAR v2.5.0 (Java 27) imported SES — 693 tracks / 89 vias. ~17 nets left (VM1/VM2 dense pads, CHG_STAT, D2/D3, SWD). Pre-existing TMC/USB pin clearances. Snapshot before: `hardware/snapshots/pre-freeroute-3.1.kicad_pcb`.
