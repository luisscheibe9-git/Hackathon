# Haven: bulk hardware cost estimate (researched 2026-11-14)

One Haven kit = 3 sensor nodes (ESP32 + power). Prices below are per node at roughly 1,000 kits (3,000 nodes). Catalog/marketplace prices, not quotes; excludes shipping, tariffs, packaging, and certification.

## Per node

| Part | Low | High | Source / note |
|---|---|---|---|
| Wi-Fi module | $1.80 (ESP32-C3-MINI-1, PCB antenna) | $2.81 (ESP32-WROOM-32UE-N4, 1,300+ tier) | TME; LCSC C701344 |
| External antenna + IPEX pigtail (32UE only) | $0 | ~$0.50 | estimate |
| Custom PCB + regulator + USB-C jack + assembly | ~$1.50 | ~$3.00 | estimate (JLCPCB-style PCBA at volume) |
| Plastic enclosure | ~$0.50 | ~$1.50 | estimate |
| 5 V 1 A USB wall adapter | $0.88 (Alibaba, UL claim unverified) | ~$3.00 (verified UL listing) | Alibaba; Brandedpromo UL E473515 ($3.04 at small qty) |
| 1 m USB cable | $0.86 | $2.08 | Global Sources listings, MOQ 1,000 |
| **Node total** | **~$6** | **~$13** | |

**Kit of 3: ~$18 to ~$39 in hardware.**

Off-the-shelf dev boards (no custom PCB) run ~$2 to $7 each on AliExpress, fine for pilots. The ESP32-DevKitC-32U is marked obsolete at DigiKey.

## Power: wall, not battery
CSI sensing keeps the radio receiving continuously (ESP32 datasheet RX is roughly 95-100 mA). A 3,000 mAh 18650 cell would last about a day, so batteries aren't practical as main power. Options:
- USB adapter + cable (above): cheapest to build, since the adapter carries the UL certification.
- Plug-in "wall wart" enclosure with a built-in AC-DC module: neater, no cable, but Haven itself then needs UL/ETL safety certification.
- Small backup battery for power outages: optional add-on, later.

## Extra costs not in the table
- FCC Part 15 testing (pre-certified Espressif modules avoid full intentional-radiator certification), and UL if the AC-DC is built in.
- Firmware flashing/test fixture, packaging, freight, import duties.

## Chip choice note
The current prototype uses original ESP32-U boards. ESP32-C3 is cheaper and supported by espressif/esp-csi, but CSI quality with its PCB antenna has not been tested; check before switching.

## Sources
- LCSC ESP32-WROOM-32UE-N4: https://www.lcsc.com/product-detail/C701344.html
- TME Espressif catalog: https://www.tme.com/us/en-us/details/esp32-c6-mini-1-n4/iot-wifi-bluetooth-modules/espressif/
- LCSC ESP32-C3 chip: https://www.lcsc.com/product-detail/C2838500.html
- Alibaba UL 5V 1A adapter: https://www.alibaba.com/product-introduction/UL-Listed-Universal-Small-Cube-Plug_1601230967235.html
- Brandedpromo UL adapter: https://www.brandedpromo.com/budget-usb-to-ac-adapter-ul-certified
- Global Sources USB-C cables: https://www.globalsources.com/category/usb-c-cables-for-sale-price_36316/?pageNum=4
- DigiKey ESP32-DevKitC-32U (obsolete): https://www.digikey.cn/en/products/detail/espressif-systems/ESP32-DEVKITC-32U/9357002
- Espressif Wi-Fi low-power guide: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/low-power-mode/low-power-mode-wifi.html
