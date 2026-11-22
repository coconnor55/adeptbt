# AdeptBT — net / pin assignment (rev 0.3)

Credit-card board. Complete this in KiCad schematic next.

## Power nets

| Net | Source | Loads |
|-----|--------|-------|
| VIN_RAW | J_PWR.1 **and J_DC tip** | PPTC → |
| VIN | after PPTC+P-FET+**SMBJ24A** | Buck in; JP_VM1/2; JP_V+ |
| GND | system | everywhere |
| USB_5V | J_USB VBUS | OR into 5V rail / charger path |
| +5V | Buck out (+ USB OR) | Charger in; JP_V+; J_AN 5V; TMC VCC_IO option |
| +3V3 | LDO from bat/sys | U1; logic; J_AN/J_DG 3V3; LEDs |
| VBAT | J_BAT+ | Charger out; LDO in (power path) |
| V+ | jumper 3V3/5V/VIN | J_PWR.3, J_PWR.5 |
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
1–4 AIN0–AIN3 (P0.02/03/04/05 or P0.28–31 — lock in sch)  
5 +3V3  
6 +5V  
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

Wire per datasheet: VS=VM, GND pad, VCC_IO=+3V3, 5VOUT cap, charge pump C, sense R (or internal), STEP/DIR/ENN/PDN_UART to U1.

## Jumpers

- JP_V+: 3V3 / 5V / VIN → V+  
- JP_VM1, JP_VM2: VIN / open(ext)  
- JP_AIN0–3: direct / ÷5V divider  
