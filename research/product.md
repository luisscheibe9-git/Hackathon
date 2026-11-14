# Product: Wi-Fi fall detection for nursing homes

_Last updated: 2026-11-13_

## Pitch
Camera-free, wearable-free fall alerts for nursing-home rooms. Small Wi-Fi sensors in each room detect a fall and alert staff with **which room, which zone (bed / floor / bathroom door), and when**.

## Who buys, who uses
- **Buyer:** nursing home / assisted living operator (director of nursing, facility admin).
- **Users:** night-shift staff (receive alerts), residents (monitored), families (peace of mind).
- **Why they care:** many falls happen at night when residents are alone and go unnoticed for a long time; cameras in bedrooms and bathrooms are a privacy problem; residents with dementia forget or remove wearables and pendants.

## Competition
| Approach | Examples | vs us |
|---|---|---|
| mmWave / UWB radar | Sensatec (RFT), Hikvision radar, LISA pilot in Montreal | **Main commercial alternative.** Camera-free, already sold to care homes and wired into nurse-call systems. More validated than Wi-Fi sensing |
| Cameras + AI | various | Strong accuracy, but a hard sell for bedrooms/bathrooms |
| Wearables / pendants | call buttons, smartwatches | Cheap, but residents don't wear them or can't press after a fall |
| Bed/chair pressure mats, PIR | many | Detect leaving bed, not falls |

**Our honest edge:** very low hardware cost (~$10-15 per ESP32 node) and Wi-Fi passes through walls (one setup can cover bedroom + bathroom door). **Our honest weakness:** Wi-Fi sensing has far fewer proven deployments than radar, and needs calibration per room.

## What a real product needs (beyond the hackathon demo)
1. **Low false-alarm rate.** Too many false alerts and staff stop responding. Measure false alarms per room per night, not just accuracy.
2. **Per-room setup that staff can do.** A guided ~10-minute calibration (empty room, walk, sit, lie on bed) when installed and after furniture moves.
3. **Multiple people.** Staff entering, roommates, visitors. Minimum: suppress or pause alerts when more than one person is moving.
4. **Nurse-call integration.** Alerts must reach the existing nurse-call system or staff phones, not just a dashboard.
5. **Reliability.** Detect when a node is offline and alert on that too.
6. **Privacy and security.** No images is a selling point; still treat data as health data (US: HIPAA), encrypt, keep processing local.
7. **Regulation.** Check whether claims trigger medical-device rules (e.g. FDA in the US). Safer early wording: "alerting aid", not "prevents falls" or "diagnoses".
8. **Validation.** A pilot in a real facility with logged true/false alerts is what buyers will ask for.

## Hackathon demo vs product
| Hackathon (this weekend) | Product (later) |
|---|---|
| 1 room, 3 ESP32-U, laptop | 3 nodes per room, small hub per floor |
| Retrain at venue | Guided calibration flow |
| Dashboard alert | Nurse-call / phone integration |
| Accuracy on our recordings | False alarms per room-night in a pilot |

## Sources
- [Sensatec radar fall alarms (RFT)](https://rft.com/fall-management)
- [How radar technology is redefining fall detection (Canadian Healthcare Technology, 2026)](https://www.canhealth.com/2026/03/31/how-radar-technology-is-redefining-fall-detection/)
- [Hikvision radar fall detection for care facilities](https://www.hikvision.com/africa/newsroom/blog/protecting-elderly-and-vulnerable-people-in-care-facilities-with)
- [Privacy-first senior fall monitoring (Butlr, vendor view)](https://www.butlr.com/articles/senior-fall-monitoring-privacy-first-strategies-2025)
- [WARE-Care nighttime fall research (U. Arizona)](https://radar.ece.arizona.edu/media/demos/ware_care/ware_care_poster.pdf)
