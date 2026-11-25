# Lessons

## 2026-11-22 — GerbView copper pile vs silk

When GerbView shows pads piled near the origin but silk refs span the board, re-export Gerbers from the current PCB with `kicad-cli` before changing placement. Stale copper Gerbers can use local footprint coords only.

## 2026-11-22 — check_silk false clean

If `check_silk.py` reports clean while GerbView shows text on pads or silk past Edge.Cuts, the checker is incomplete. Require text×pads, text×F.SilkS/F.Fab, and footprint silk/fab off-board — not text×text alone. Parse both single-line and multiline KiCad pad/fp_line forms or solids stay at 0.

## 2026-11-22 — USB edge vs label rule

GCT USB4105 footprint marks **PCB Edge** at local y=3.1. Placing origin there hangs **F.Fab** (and looks like silk) past Edge.Cuts. Do not allowlist `J_USB` overhang — require F.SilkS, F.Fab, and **pads** on-board. Put the `J_USB` label on the board side (right of pads) as `gr_text`; hide the footprint ref. Case catch can still meet the shell at the left edge without copper/fab past the cut.

## 2026-11-22 — footprint layer bbox regex

When parsing KiCad `fp_rect`/`fp_line`, take the layer tag from the **same** graphic only (split per object). A `[\s\S]*?\(layer "F.Fab"\)` from the first rect can latch onto a later rect's layer and attribute F.CrtYd extents to F.Fab.

## 2026-11-23 — silk clean ≠ body clear

`check_silk.py` must fail on courtyard/body overlap (not silk text alone). Zone the board (power / MCU / steppers) before packing discretes. U1 antenna tip belongs on the board edge so the power area is not crushed into the leftover strip.

## 2026-11-23 — TE courtyard owns the edge strip

J_STEP1/2 F.CrtYd spans ~x 60–84 and ~10 mm in from the long edge. Do not place headers, electros, or pin silk in that band. Keep AN/DG west of x≈60 and keep bottom-row parts above the STEP2 silk line (~y 42).

## 2026-11-23 — 1 mm outline clear + screw squares

`BODY_CLEAR_MM` keep-away uses F.Fab (edge TE: F.SilkS), not F.CrtYd. Mounting holes need an explicit 6×6 mm F.SilkS square keepout — the hole courtyard circle is not parsed as a body. On this density, put AN/DG pin silk east of the headers so the power island stays free; JP_VM must be vertical on the south edge — there is no 1 mm horizontal slot between DG and STEP2.

## 2026-11-23 — F.Fab is not ink; USB Edge at +Y

`F.Fab` is assembly outline (not silkscreen). `F.SilkS` is the printed ink. On GCT USB4105, "PCB Edge" is local +Y; at board angle 90° that edge faces left — do not rotate to 180° to "fix" Fab. When silk looks clear but U6 still collides with DG, check F.CrtYd vs neighbor F.Fab, not Fab×Fab alone.

## 2026-11-23 — JST BAT needs plug approach room

Do not park `J_BAT` under the STEP1 x-band mid-board. Put it east of the barrel and west of STEP1 with the PH mating face open (ang 0 → south) so the cable can seat.

## 2026-11-23 — pcbnew owns the board file

When the board has been laid out in pcbnew, do not run `tools/gen_adeptbt_pcb.py` — it rewrites `hardware/adeptbt.kicad_pcb` and GerbView shows the generator floorplan. Keep placement in the `.kicad_pcb` file; re-export Gerbers from that file only.

## 2026-11-23 — append footprints at board end only

Footprint `.kicad_mod` files contain `(embedded_fonts no)`. When splicing parts into a `.kicad_pcb`, insert before the **last** board-level `(embedded_fonts no)`, never the first match, or new footprints nest inside an existing one.

## 2026-11-23 — symbol unit prefix must match entry name

KiCad rejects `Invalid symbol unit name prefix` when a lib_symbols entry is renamed (or `extends` is flattened) but nested units still use the old name (`AP63200WU_0_1` under `AP63205WU`). Rename every `Old_U_S` unit to `New_U_S` in `extract_symbol` / `rename_symbol_tree`. Without that, the schematic fails to load and Update PCB / ratsnest never run.

## 2026-11-23 — schematic pin labels use sheet Y-flip

On a KiCad sheet, symbol instance pin tips are at `(ix + lx, iy − ly)` for library pin local `(lx, ly)`. Labels at `iy + ly` sit on the wrong pin (U4 GND/SW/FB swap). Always place pin labels through `pin_xy` / `label_pin`. Power-symbol and `PWR_FLAG` pins sit at the instance origin — do not offset them. Do not put `PWR_FLAG` on a net that already has a regulator Power-output pin.

## 2026-11-23 — mounting holes are M1–M4; jumpers on sch

Corner screw holes use refs **M1–M4** (not H1–H4). `JP_V+`, `JP_VM1`, and `JP_VM2` belong on the schematic with the nets in `docs/NETLIST.md`, not PCB-only.
## 2026-11-23 — KiCad refs must end in a digit

Update PCB / annotation rejects refs whose last character is not a digit (`J_USB`, `JP_V+`, `C40B`). Always use a trailing number (`J_USB1`, `JP_V+1`, `C402`). Power refs starting with `#` are exempt.

## 2026-11-23 — every footprint pad needs a symbol pin

Update PCB warns `No net found for component X pad Y (no pin Y in symbol)` when the footprint has pads the symbol omits (`SH`, USB mirrored A/B, `MP`). Match pad names 1:1 (GCT → `USB_C_GCT_16P`; JST/barrel → `*_MountingPin` with `MP`→GND). Stack same-net pins on one tip; NC unused SBU.

## 2026-11-24 — status LED refs are PWR1/CHG1/USR1

Do not use bare `PWR`/`CHG`/`USR` as references — KiCad annotation requires a trailing digit. Status LEDs are `PWR1`, `CHG1`, `USR1` (values may still read PWR/CHG/USR).

## 2026-11-24 — PCB version owner is title_block + silk

Board rev lives in `hardware/adeptbt.kicad_pcb` title_block `(rev …)` and silkscreen `rev x.y` (from **3.9**: **B.SilkS**, mirrored, with `AdeptBT`). Keep both in sync and only increment z on later ships. Do not reset to an older 2.x series. JLCPCB does not charge extra for bottom silk vs top — include `.GBO` in the Gerber ZIP.

## 2026-11-24 — Freerouting leftovers: no invented crossings

For Freerouting leftovers on this density, re-export DSN and run Freerouting again. Do not A*/bridge open pairs through existing copper — that creates shorts. Safe cleanup: widen to ≥0.2 mm, shrink `ant_keepout` south of U1 pads, set `GND_F` pad connection FULL, refill. Leave pour islands if bridging crosses +5V.

## 2026-11-24 — ant_keepout must ban copperpour

`ant_keepout` with `copperpour allowed` still fills GND on F/In1/In2/B under the U1 tip. Set `copperpour not_allowed` (and refill). Keepout box stays south of the south pad row (~y≥50).

## 2026-11-24 — Freerouting leaves zero GND vias

Freerouting with `ignore_net_classes=GND` routes signals on In1/In2 and adds **no** GND stitch vias. After SES import, place clearance-checked through vias on GND (and in-island vias for orphan F.Cu pours at C41/C2/USB). Blind F-only bridges often short; through vias must clear foreign copper on all four layers.

## 2026-11-24 — check_silk edge refs and Y-down rotate

`EDGE_BODY_OUTLINE` entries are stems (`J_DC`); match with digit-stripped refs (`J_DC1`). KiCad board_xy is Y-down: `fx+lx*c+ly*s`, `fy-lx*s+ly*c`. Ignore `B.SilkS` `gr_text` in front silk×solid checks.

## 2026-11-24 — JLCPCB CPL is not KiCad pos CSV

JLCPCB rejects KiCad `Ref,PosX,PosY,Rot,Side`. Convert to `Designator,Mid X,Mid Y,Layer,Rotation` with `Top`/`Bottom`, positive mm (negate KiCad’s negative Y). Owner: `docs/JLCPCB_CPL.csv`.

## 2026-11-24 — JLCPCB BOM designators must match CPL exactly

Do not use ranges (`R2-R6`, `M1-M4`) in the assembly BOM. Use comma lists (`R2,R3,R4,R5,R6`). Every BOM designator must appear in the CPL (and vice versa for SMT). Omit mounting holes from the assembly BOM.

## 2026-11-24 — JLCPCB auto-match can pick the wrong package or part

Do not trust Comment/value keyword matches. Reject 01005 for 0402 footprints, THT resistors for 1206 sense, and isolators for headers named DIGITAL. Lock LCSC in `JLCPCB_ASSEMBLY_BOM.csv` before re-upload.

## 2026-11-25 — Q_PMOS / Q_NPN pin lib offsets must match the library

For Q_PMOS (G=pin1, S=pin2, D=pin3), the KiCad library offsets are G=(-5.08,0), S=(2.54,-5.08), D=(2.54,5.08). Swapping S and D swaps VIN/VIN_F on Q1. Always verify lib offsets from the `lib_symbols` block in the schematic snapshot — do not guess from the schematic symbol orientation. When a wire crosses a pin that falls between its endpoints, KiCad connects that pin to the wire net; route around or use labels.
