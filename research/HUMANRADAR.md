# HumanRadar video research

Reviewed November 13, 2026, using the video transcript, final demo footage, and the creator's repository.

## What the demo shows

Basically Homeless builds a live map of people in his house. In the final demo, the phone's camera view shows a floor-plan inset and a red box marking an estimated person location beyond the wall. The overlay combines detections from fixed radar sensors with the position and heading of the person holding the phone. [Final demo, 8:19](https://www.youtube.com/watch?v=Lj3wN7UPukg&t=499s)

## How the system works

1. Fixed HLK-LD2450 24 GHz mmWave radar modules report target positions relative to each sensor. An ESP32-C3 sends each node's detections over Wi-Fi to a Node.js server. The repository lists up to three targets and a range of up to six meters per sensor. [Hardware and architecture](https://github.com/Mr-Homeless/HumanRadar#how-it-works)
2. The server uses the sensor placements and orientations to put detections on a shared floor plan. It publishes updates over WebSocket at 10 Hz for the dashboard, smartwatch, and phone views. [System architecture](https://github.com/Mr-Homeless/HumanRadar#how-it-works)
3. A wearable DW3000 ultra-wideband tag measures distances to fixed anchors. The server estimates the wearer's position by trilateration and filters nearby detections to suppress the wearer. The phone supplies the viewing direction and camera feed for the AR overlay. [Repository](https://github.com/Mr-Homeless/HumanRadar) · [Phone and UWB setup, 6:42](https://www.youtube.com/watch?v=Lj3wN7UPukg&t=402s)

## Limits observed in the demo

- Moving the handheld radar produced false detections. The whole-home build uses fixed nodes so their readings can be placed on the map consistently. [Handheld test, 2:17](https://www.youtube.com/watch?v=Lj3wN7UPukg&t=137s)
- The demo required calibration and filtering near the wearer. The footage shows a working example in the creator's house. Tracking accuracy across layouts, detection reliability through different wall materials, and false-positive rates remain unverified. [Calibration discussion, 8:32](https://www.youtube.com/watch?v=Lj3wN7UPukg&t=512s)

## Hackathon relevance

Our prototype uses Wi-Fi channel state information (CSI) from three ESP32 boards to detect falls and identify the room zone without a camera or wearable. HumanRadar uses separate mmWave radar modules for person tracking and a wearable UWB tag for the phone overlay. Its live display is a reference for showing an event's estimated zone and time in our dashboard. The demo provides no Wi-Fi CSI fall-detection results. See [our CSI approach](approach.md) for the proposed detector.

## Where to continue

The [HumanRadar README](https://github.com/Mr-Homeless/HumanRadar#readme) has the component list, wiring, and setup. In that repository, `HumanRadar_WiFi/` contains the radar node firmware, `HumanRadar_UWB_Anchor/` and `HumanRadar_UWB_Tag/` contain the ranging firmware, and `HumanRadar_Server/` contains the server and browser clients.
