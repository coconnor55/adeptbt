# AdeptBT — decoupling capacitors

Values locked from datasheets / reference circuits. Place next to the related pins; short loops to GND.

## On the board now (U1 / U2 / U3 / USB / VIN)

| Ref | Value | Pkg | Nets | Role | Source |
|-----|-------|-----|------|------|--------|
| C1 | 100 nF | 0402 | +3V3–GND | U1 local HF | Board practice at VDD |
| C2 | 1 µF | 0603 | +3V3–GND | U1 bulk (DEC4-style) | Raytac MDBT50Q ref circuit |
| C3 | 100 nF | 0402 | USB_5V–GND | USB HF | USB receptacle practice |
| C4 | 10 µF | 0805 | USB_5V–GND | USB bulk | USB receptacle practice |
| C10 | 22 nF ≥50 V | 0603 | CPO1–CPI1 | U2 charge pump | TMC2209 DS |
| C11 | 100 nF | 0402 | VCP1–VM1 | U2 VCP | TMC2209 DS |
| C12 | 4.7 µF | 0805 | 5VOUT1–GND | U2 5VOUT | TMC2209 DS 2.2–4.7 µF |
| C13 | 100 nF | 0402 | +3V3–GND | U2 VCC_IO | Local at pin 15 |
| C14 | 100 nF | 0402 | VM1–GND | U2 VS ceramic | TMC2209 DS |
| C15 | 100 µF 25 V | Elec 6.3×5.3 | VM1–GND | U2 VS bulk | TMC2209 DS ≥100 µF near driver |
| C20–C25 | same as C10–C15 | | U3 / VM2 / 5VOUT2 | | Same |
| C30 | 100 nF | 0402 | VIN–GND | VIN HF | Power entry |
| C31 | 100 µF 25 V | Elec 6.3×5.3 | VIN–GND | VIN bulk | Shared motor/logic supply |

`5VOUT1` / `5VOUT2` are **local** TMC regulator outputs (not the board `+5V` buck rail).

## Power ICs (on schematic rev 0.5 / PCB rev 2.1)

| Ref | Value | Pkg | Nets | Role | Source |
|-----|-------|-----|------|------|--------|
| C40 | 10 µF | 0805 | VIN–GND | AP63205 VIN bulk | AP63205 DS / EVM |
| C40B | 100 nF | 0402 | VIN–GND | AP63205 VIN HF | AP63205 DS / EVM |
| C41 / C41B | 22 µF each | 0805 | +5V–GND | AP63205 out | AP63205 Table 3 |
| C42 | 100 nF | 0402 | BST–SW | AP63205 bootstrap | AP63205 EVM |
| C50 | 10 µF | 0805 | +5V–GND | AMS1117 input | AMS1117 typical |
| C51 | 22 µF | 0805 | +3V3–GND | AMS1117 output | AMS1117 typical |
| C60 | 4.7 µF | 0805 | VBAT–GND | MCP73871 battery | MCP73871 DS |
| C61 | 4.7 µF | 0805 | +5V–GND | MCP73871 IN/OUT | MCP73871 DS |

## Notes

- VS / VIN electrolytics: ≥25 V rating (VIN to 18 V).
- Charge-pump `22 nF` must be ≥50 V.
- Prefer X5R/X7R ceramics for HF parts.
