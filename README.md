# AdeptBT

Credit-card sized nRF52840 control board (Raytac MDBT50Q-1MV2).

## Features

- Dual TMC2209 stepper drivers
- Two 2N2222 low-side outputs with jumperable V+ (3.3 V / 5 V / VIN)
- USB-C programming; LiPo (JST) with ~400–500 mA charge; VIN 5–18 V (P-FET + TVS + PPTC)
- Analog header (4× AIN, jumperable 3.3/5 V dividers) and digital GPIO header
- 6-pin screw terminals: steppers (`A1 A2 B1 B2 VM GND`) and power/outs (`VIN GND V+ OUT1 V+ OUT2`)

## Hardware

KiCad project: [`hardware/`](hardware/) — schematic, PCB placement, silkscreen (rev 0.4 target).

See [`docs/DESIGN.md`](docs/DESIGN.md), [`docs/JLCPCB_BOM.md`](docs/JLCPCB_BOM.md), [`hardware/README.md`](hardware/README.md). Repo decisions and open work: [`memory/`](memory/).

Open `hardware/adeptbt.kicad_pro` in KiCad 10 to finish power discretes, routing, and Gerbers.
