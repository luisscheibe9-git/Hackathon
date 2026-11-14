# Wi-Fi sensing with ESP32-S3 boards

Reviewed November 13, 2026. This note records Better Stack’s demo and the published kit documentation. The performance figures are the creator’s measurements. We have yet to reproduce the experiment in this project.

> **Note for our hardware:** this demo and kit need ESP32-S3 boards. We have 3x ESP32-U (original ESP32 chip), which RuView and this kit don't support, so we can't reproduce it as-is. We use espressif/esp-csi instead (see [approach.md](approach.md)). The method (camera-labeled training, then CSI-only classification) still applies.

## What the demo did

Wi-Fi packets travel along multiple paths as they reflect off people, furniture, and walls. Channel state information (CSI) measures how the received signal changes across frequency subcarriers. The demo used three roughly $10 ESP32-S3 boards running patched RuView firmware. The boards collected nine sensing links in total, including links from the router and between the boards. [How sensing works](https://www.youtube.com/watch?v=9Tihk9_jUyo&t=73s) · [Board setup](https://www.youtube.com/watch?v=9Tihk9_jUyo&t=241s)

During roughly nine minutes of training, browser-based MediaPipe pose detection generated activity labels that the software paired with CSI samples. The demo then used CSI alone to classify activity with the webcam covered. The separate camera in the video let viewers compare the predictions with the presenter’s movements. [Training](https://www.youtube.com/watch?v=9Tihk9_jUyo&t=302s) · [Camera-covered demo](https://www.youtube.com/watch?v=9Tihk9_jUyo&t=424s)

## Reported results

The creator recorded a separate evaluation session in the same living room with the same person and board placement. Overall accuracy was **79.5%** across eight states. The kit README also reports **76.3%** for router links alone and **63.1%** using motion magnitude alone. [Video results](https://www.youtube.com/watch?v=9Tihk9_jUyo&t=377s) · [Kit results](https://github.com/andrisgauracs/wifi-sensing-kit#what-to-expect-measured-not-marketing)

| State | Correct |
| --- | ---: |
| Empty room | 100% |
| Jumping | 97% |
| Sitting | 93% |
| Spinning | 92% |
| Standing | 84% |
| Squatting | 79% |
| Walking | 70% |
| Waving | 13% |

At 7:33 the presenter discusses occupancy as a binary task and reports **96%** for their room. The 100% in the table is the empty-room class result in the eight-state evaluation. The presenter raises through-wall sensing as a privacy concern. The measured test used boards connected to their own Wi-Fi network in one room. [Occupancy and privacy discussion](https://www.youtube.com/watch?v=9Tihk9_jUyo&t=453s)

## Reproduction and hackathon fit

- Start with the demo’s [Wi-Fi Sensing Kit](https://github.com/andrisgauracs/wifi-sensing-kit). Its build script applies a patch to [RuView](https://github.com/ruvnet/ruview) firmware identified as v0.8.8 in the kit README. The kit documents three ESP32-S3 boards with at least 8 MB flash, USB data cables and power, a 2.4 GHz Wi-Fi network, a webcam, and ESP-IDF 5.4 or 5.5. It lists macOS or Linux for setup and Windows for the dashboards.
- Follow the kit’s build and flash steps, place the boards, run the local server, and use its movement dashboard to record training and a separate test. Run `python kit/evaluate.py` in the kit environment for the score and confusion table. [Kit setup and training](https://github.com/andrisgauracs/wifi-sensing-kit#setup)
- A single-room occupancy demo is a possible hackathon scope if the event allows the hardware. Check empty versus occupied in a fresh test and include a person sitting still. Test a second person or move a board if the pitch depends on portability. The published scores cover one person and one room, and the presenter expects to retrain after changes in person or board placement. [Demo limitations](https://www.youtube.com/watch?v=9Tihk9_jUyo&t=528s)
