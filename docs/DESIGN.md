# AdeptBT — locked design

Credit-card PCB (~85.6 × 53.98 mm), 4-layer preferred.

## MCU
- Raytac MDBT50Q-1MV2 (nRF52840, chip antenna)

## Motion / outputs
- 2× TMC2209 (always fitted): STEP/DIR/EN/UART each
- 2× 2N2222 low-side outs + flyback diodes
- V+ jumperable: 3.3 V / 5 V / VIN

## Power
- USB-C: program + can run/charge MCU path
- LiPo JST-PH + **MCP73871** charger ~400–500 mA (DNP OK)
- VIN **5–18 V**: P-FET reverse + **SMBJ24A** + PPTC
- Buck **AP63205** → 5 V; LDO **AMS1117-3.3** → module
- Stepper VM jumperable to VIN or external (ext >18 V needs own protect)

## Connectors (layout)
- Long edge A: 2× TE 2383941-6 — steppers `A1 A2 B1 B2 VM GND`
- Long edge B: 1× TE 2383941-6 — `VIN GND V+ OUT1 V+ OUT2` + **5.5×2.1 barrel** (`J_DC`) on `VIN_RAW`
- Short edge: USB-C
- Analog / digital / SWD headers; BAT JST

## Mechanical
- 4× M2 mounting holes (corners)
- Silkscreen: AdeptBT, pin labels, jumper legends

## Part SKUs (JLCPCB-first — see `JLCPCB_BOM.md`)
- MCU: Raytac MDBT50Q-1MV2 (**C5118826**)
- Drivers: TMC2209-LA (**C465949**)
- Screws: TE **2383941-6** (**C3816695**) 7 A
- Charger: **MCP73871** (**C5121473**)
- TVS: **SMBJ24A**; barrel: 5.5×2.1 on VIN
