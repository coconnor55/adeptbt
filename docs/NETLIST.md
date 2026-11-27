# AdeptBT — net / pin assignment (rev 0.5)

Credit-card board. Complete this in KiCad schematic next.

## Power nets

| Net | Source | Loads |
|-----|--------|-------|
| VIN_RAW | J_PWR.1 **and J_DC tip** | PPTC → |
| VIN | after PPTC+P-FET+**SMBJ24A** | Buck in; JP_VM1/2; JP_V+ |
| GND | system | everywhere |
| USB_5V | J_USB VBUS | OR into 5V rail / charger path |
| +5V | Buck out (+ USB OR) | Charger in; J_AN 5V (sensor supply); TMC VCC_IO option |
| +3V3 | LDO from bat/sys | U1; logic; J_AN/J_DG 3V3; JP_V+; LEDs |
| VBAT | J_BAT+ | Charger out; LDO in (power path) |
| V+ | jumper 3V3 / VIN | J_PWR.3, J_PWR.5 |
| VM1 | jumper VIN/ext | J_STEP1.5 → U2 VS |
| VM2 | jumper VIN/ext | J_STEP2.5 → U3 VS |

## Connectors

### J_STEP1 / J_STEP2 (TE 2383941-6)
1 A1 → driver OA1/OA2 pair per TMC coil A  
2 A2  
3 B1  
4 B2  
5 VM  
6 GND  

### J_PWR
1 VIN_RAW  
2 GND  
3 V+  
4 OUT1 (Q2 collector/open)  
5 V+  
6 OUT2  

### J_DC (5.5×2.1 barrel)
1 GND (sleeve)  
2 VIN_RAW (tip / center)  
3 switch (NC if unused)  

### J_AN (1×07)
1–4 AIN0–AIN3 (3.3 V range, direct to MCU — external divider if needed)  
5 +3V3  
6 +5V (sensor supply only; not a divider rail)  
7 GND  

### J_DG (1×06)
1–4 D0–D3 GPIO  
5 +3V3  
6 GND  

### J_SWD (1×05)
SWDIO, SWCLK, GND, +3V3, RESET  

### J_USB / J_BAT
USB-C: VBUS, D+, D−, CC1/CC2, GND  
BAT: + / − (polarity marked)  

## U1 MDBT50Q-1MV2 (GPIO lock — rev 0.3)

| Function | Module pin / GPIO |
|----------|-------------------|
| USB | VBUS / D+ / D− (native) |
| AIN0–3 | P0.02 / P0.03 / P0.04 / P0.05 |
| OUT1_DRV / OUT2_DRV | P0.06 / P0.08 → 1k → MMBT2222A |
| LED_USER | P0.07 |
| TMC_UART (shared) | P0.14 → both PDN_UART |
| STEP1 STEP / DIR / EN | P0.21 / P0.20 / P0.13 |
| STEP2 STEP / DIR / EN | P0.16 / P0.15 / P0.17 |
| D0–3 | P0.23 / P0.22 / P1.00 / P0.24 |
| CHG_STAT | P0.25 |
| SWD / nRESET | SWDIO / SWDCLK / P0.18 |

## U2 / U3 TMC2209

Wire per datasheet: VS=VM, GND pad, VCC_IO=+3V3, 5VOUT cap, charge pump C, sense R `RSA`/`RSB` **0.10 Ω** to GND on `BRA`/`BRB`, STEP/DIR/ENN/PDN_UART to U1.

## Power path

`VIN_RAW` → F1 PPTC → `VIN_F` → Q1 AO3407 (S=`VIN_F`, D=`VIN`, G=GND) → D1 SMBJ24A (`VIN`–GND) → `VIN` → U4 AP63205 → `SW`/`L1` → `+5V` → U6 AMS1117 → `+3V3`. U5 MCP73871 on `+5V` / `VBAT` / `CHG_STAT` (PROG1=2 kΩ).

## Jumpers

- JP_V+1: 1×3 — 3V3 / V+ / VIN (short adjacent pins: 3V3↔V+ or V+↔VIN)  
- JP_VM1, JP_VM2: 1×2 — VIN / EXT (open = external VM)  
- No JP_AIN — AIN is 3.3 V only; use an external divider when needed
- Net class **Analog** (clearance **0.3 mm**, width 0.25): `AIN*` only — in `adeptbt.kicad_pro`. `VREF_*` stays **Signal** (tight TMC neighborhood).  

## Decoupling

Owner: [`docs/DECOUPLING.md`](DECOUPLING.md). TMC `5VOUT1`/`5VOUT2` are local (not board `+5V`). Cap refs C1–C31 + buck/LDO/charger caps on schematic rev 0.5 / PCB rev 2.1.
