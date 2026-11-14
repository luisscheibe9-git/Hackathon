# Sources

Format: link, what it is, why it matters to us.

## Videos

- **[I Turned My Wi-Fi Into a Surveillance System](https://www.youtube.com/watch?v=9Tihk9_jUyo)** (Better Stack). Demo of Wi-Fi sensing on ~$10 ESP32-S3 boards, apparently the RuView project. Proof that a 3-board setup works for presence/activity. Note: the video itself has not been fully transcribed here; details come from the write-up below.

## Write-ups

- **[Your Wi-Fi is watching: here's what it can see](https://www.stork.ai/blog/your-wi-fi-is-watchingheres-what-it-can-see)** (Stork.ai). Covers a 3x ESP32-S3 RuView demo: presence 96%, sitting 93%, walking 70%, waving 13%, 79.5% overall on 8 activities. Accuracy dropped to 11% in an untrained room. Viral pose skeleton was partly simulated. Falls and location not tested.
- **[ESP Wi-Fi CSI detects humans with Wi-Fi signals only](https://www.cnx-software.com/2022/08/08/esp-wifi-csi-detects-humans-with-wifi-signals-only-no-sensor-needed/)** (CNX Software). Intro to Espressif's esp-csi.

## Code

- **[ruvnet/RuView](https://github.com/ruvnet/RuView)** (MIT, beta). Wi-Fi CSI sensing platform. ESP32-S3/C6 only; recommends 2+ nodes (4-6 ideal). Has presence, zone occupancy, threshold fall-detection module, Home Assistant/MQTT. Live pose model is weak (3% PCK@20); vital signs unvalidated. Has a Docker demo with simulated data.
- **[espressif/esp-csi](https://github.com/espressif/esp-csi)**. Official CSI framework for the ESP32 family. Lower-level, wider board support.

## Papers

- **[ESP32-S3 3-board fall detection](https://symposium2026.pcshstrg.ac.th/uploads/projects/83/abstract_pdf_20260714_210549.pdf)** (student symposium 2026). Very close to our idea: 3x ESP32-S3, classes EMPTY/WALK/FALL, 10,563 samples, 91.53% accuracy. Main error: FALL confused with EMPTY. Preliminary, student-level.
- **[Deep learning fall detection on Wi-Fi CSI](https://doaj.org/article/518fb30284034d008214438522431e9d)** (IEEE Access, 2023). 700+ samples, 4 rooms, >96% accuracy. Controlled conditions.
- **[Three-ESP32 localization testbed](https://www.preprints.org/manuscript/202601.2295/download/final_file)** (preprint, 2026). 3 ESP32 transceivers in a 6x4 m lab, 35 grid points, device-free fingerprinting. Shows zone/grid localization with our node count.
- **[ESP32 as a CSI sensing platform](https://rgu-repository.worktribe.com/OutputFile/2071661)** (RGU). Finds ESP32 CSI viable and low-cost for sensing.
- **[Smartphone IMU + Wi-Fi CSI fall detection](https://arxiv.org/abs/2412.09980)** (arXiv, 2024). CNN on CSI reported 99% as a secondary check. Controlled setting.
