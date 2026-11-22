# Board intent & product

2026-11-22. AdeptBT is a credit-card nRF52840 control board (Raytac MDBT50Q-1MV2), dual TMC2209, dual low-side outs, USB-C + LiPo + VIN. Spec lives in `docs/DESIGN.md` / `docs/NETLIST.md`.

**First commercial use:** [film-scanner-120](https://github.com/coconnor55/film-scanner-120) (or local `Documents/GitHub/film-scanner-120`). That product runs **two steppers + board from one 12 V wall wart**. Motor VM and logic share VIN via jumpers/buck — not a separate Xiao + breakout stack.

Battery + MCP73871 + JST stay on the PCB even when unused: BOM delta is negligible; leave those parts **DNP** on scanner SKUs if desired. Same board serves portable / LiPo builds later.

VIN may go to **18 V** (auto). Wall-wart inlet is **5.5×2.1 mm** barrel (`J_DC`) in parallel with screw `VIN_RAW`.

Related EcoSpring / pump work was a prior chat seed; AdeptBT is the shared motion+I/O board, not EcoSpring-specific.
