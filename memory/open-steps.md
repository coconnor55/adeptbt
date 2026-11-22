# Open steps

- Wire power discretes on schematic: PPTC, P-FET, **SMBJ24A**, AP63205, **MCP73871**, AMS1117, TMC sense Rs / charge-pump caps. Owners: `docs/NETLIST.md`, `tools/gen_adeptbt_sch.py` / KiCad GUI. Stopped: labels + majors only so far.
- Confirm TE 2383941-6 pad geometry vs datasheet (current footprint is approximate). Owner: `hardware/libs/AdeptBT.pretty/TE_2383945-6_…`.
- Pick live LCSC SKUs for barrel, AO3407-class P-FET, PPTC, SMBJ24A at order time. Owner: `docs/JLCPCB_BOM.md`.
- PCB: route, GND pour, DRC, fab Gerbers. Owner: `hardware/adeptbt.kicad_pcb`. Placement + silk only today.
- Optional: leave BAT/MCP73871 DNP note on scanner fab variant / assembly drawing.
- ~~Commit/push uncommitted 0.3–0.4 docs, libs, generators.~~ Done on gitpush 2026-11-22.
