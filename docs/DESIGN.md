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
- LiPo JST-PH + charger ~400–500 mA
- VIN 5–18 V: P-FET reverse + TVS + PPTC
- Buck → 5 V; LDO → 3.3 V (module)
- Stepper VM jumperable to VIN or external (24 V = external protection)

## Connectors (layout)
- Long edge A: 2× 6-pin screw — steppers `A1 A2 B1 B2 VM GND`
- Long edge B: 1× 6-pin screw — `VIN GND V+ OUT1 V+ OUT2`
- Short edge: USB-C
- Analog header: 4× AIN + 3V3 + 5V + GND; per-AIN jumper Direct / ÷5 V
- Digital header: 4× GPIO + 3V3 + GND
- SWD header, BAT JST

## Mechanical
- 4× M2 mounting holes (corners)
- Silkscreen: AdeptBT, pin labels, jumper legends

## Part SKUs (targets)
- Screw terminals: Phoenix MKDS 1/6-3,81 SMD (or equiv. 6-pos 3.81 mm SMD)
- Jumpers: 2.54 mm pin headers
