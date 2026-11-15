#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_wifi.h>
#include <esp_now.h>
#include <atomic>

std::atomic<unsigned long> frames{0};
uint8_t accessPoint[6];
QueueHandle_t samples;
const char *standaloneSsid = "Stillpoint-CSI";
const uint8_t board2[] = {0x68, 0x09, 0x47, 0x9f, 0x27, 0xf4};
const uint8_t board3[] = {0x68, 0x09, 0x47, 0x1a, 0x80, 0xac};
bool capturePeer = false;

struct CsiSample {
  uint32_t timestamp;
  int8_t rssi;
  bool firstWordInvalid;
  bool peer;
  uint8_t data[128];
};

void onCsi(void *, wifi_csi_info_t *info) {
  if (!info || !info->buf || info->len < sizeof(CsiSample::data)) return;
  const bool peer = capturePeer && memcmp(info->mac, board2, 6) == 0;
  if (peer || memcmp(info->mac, accessPoint, 6) == 0) {
    frames.fetch_add(1, std::memory_order_relaxed);
    CsiSample sample{info->rx_ctrl.timestamp, info->rx_ctrl.rssi, info->first_word_invalid, peer, {}};
    memcpy(sample.data, info->buf, sizeof(sample.data));
    xQueueSend(samples, &sample, 0);
  }
}

bool startPeerProbe() {
  if (esp_now_init() != ESP_OK) return false;
  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, board3, sizeof(board3));
  peer.ifidx = WIFI_IF_STA;  // channel 0 follows the gateway's current channel
  esp_now_rate_config_t rate{};
  rate.phymode = WIFI_PHY_MODE_HT20;
  rate.rate = WIFI_PHY_RATE_MCS0_LGI;
  if (esp_now_add_peer(&peer) == ESP_OK && esp_now_set_peer_rate_config(board3, &rate) == ESP_OK) return true;
  esp_now_deinit();
  return false;
}

void setup() {
  Serial.begin(460800);
  samples = xQueueCreate(64, sizeof(CsiSample));
  Serial.setTimeout(2000);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
}

void loop() {
  const unsigned long listenUntil = millis() + 3000;
  while (!Serial.available() && (long)(listenUntil - millis()) > 0) {
    delay(20);
  }
  const bool configuredOverUsb = Serial.available();
  String ssid = configuredOverUsb ? Serial.readStringUntil('\n') : standaloneSsid;
  String password = configuredOverUsb ? Serial.readStringUntil('\n') : "stillpoint-demo";
  WiFi.begin(ssid.c_str(), password.c_str());
  password = "";
  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 25000) {
    delay(100);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("JOIN_FAILED status=%d\n", WiFi.status());
    WiFi.disconnect();
    return;
  }

  Serial.printf("JOINED ip=%s gateway=%s channel=%d rssi=%d\n",
                WiFi.localIP().toString().c_str(), WiFi.gatewayIP().toString().c_str(),
                WiFi.channel(), WiFi.RSSI());
  memcpy(accessPoint, WiFi.BSSID(), sizeof(accessPoint));
  const bool standalone = ssid == standaloneSsid;
  uint8_t station[6]{};
  esp_wifi_get_mac(WIFI_IF_STA, station);
  const bool sendPeer = standalone && memcmp(station, board2, 6) == 0;
  const bool peerProbeReady = sendPeer && startPeerProbe();
  capturePeer = standalone && memcmp(station, board3, 6) == 0 &&
                esp_wifi_set_promiscuous(true) == ESP_OK;
  if (sendPeer) Serial.printf("PEER_PROBE %s\n", peerProbeReady ? "ready" : "failed");
  if (capturePeer) Serial.println("PEER_CSI listening for ESP32 #2");
  wifi_csi_config_t config = {};
  config.lltf_en = true;
  config.htltf_en = true;
  config.channel_filter_en = true;
  const esp_err_t configured = esp_wifi_set_csi_config(&config);
  const esp_err_t registered = esp_wifi_set_csi_rx_cb(onCsi, nullptr);
  const esp_err_t enabled = esp_wifi_set_csi(true);
  if (configured != ESP_OK || registered != ESP_OK || enabled != ESP_OK) {
    Serial.printf("CSI_INIT_FAILED config=%d callback=%d enable=%d\n", configured, registered, enabled);
  }
  unsigned long lastCount = millis();
  unsigned long lastProbe = millis();
  unsigned long lastPeerProbe = millis();
  WiFiUDP probe;
  uint8_t relay[136] = {'C'};
  if (standalone) {
    probe.begin(50001);
    esp_wifi_get_mac(WIFI_IF_STA, relay + 1);
  }
  while (WiFi.status() == WL_CONNECTED) {
    if (peerProbeReady && millis() - lastPeerProbe >= 40) {
      lastPeerProbe = millis();
      const uint8_t signal[] = {'C', 'S', 'I'};
      esp_now_send(board3, signal, sizeof(signal));
    }
    if (standalone && millis() - lastProbe >= 35) {
      lastProbe = millis();
      if (probe.beginPacket(WiFi.gatewayIP(), 50000)) {
        probe.write(reinterpret_cast<const uint8_t *>("CSI"), 3);
        probe.endPacket();
      }
      while (probe.parsePacket() > 0) {
        probe.clear();
      }
    }
    CsiSample sample;
    if (xQueueReceive(samples, &sample, pdMS_TO_TICKS(20))) {
      if (standalone) {
        relay[0] = sample.peer ? 'P' : 'C';
        relay[7] = static_cast<uint8_t>(sample.rssi);
        memcpy(relay + 8, sample.data, sizeof(sample.data));
        if (probe.beginPacket(WiFi.gatewayIP(), 50000)) {
          probe.write(relay, sizeof(relay));
          probe.endPacket();
        }
      }
      if (!configuredOverUsb || sample.peer) {
        continue;
      }
      const char digits[] = "0123456789abcdef";
      char hex[sizeof(sample.data) * 2 + 1];
      for (size_t i = 0; i < sizeof(sample.data); ++i) {
        hex[i * 2] = digits[sample.data[i] >> 4];
        hex[i * 2 + 1] = digits[sample.data[i] & 15];
      }
      hex[sizeof(hex) - 1] = '\0';
      Serial.printf("CSI,%lu,%d,%d,%s\n", (unsigned long)sample.timestamp,
                    sample.rssi, sample.firstWordInvalid, hex);
    }
    if (millis() - lastCount >= 1000) {
      lastCount = millis();
      Serial.printf("CSI_FRAMES %lu\n", frames.exchange(0, std::memory_order_relaxed));
    }
  }
  esp_wifi_set_csi(false);
  if (capturePeer) esp_wifi_set_promiscuous(false);
  if (peerProbeReady) esp_now_deinit();
  xQueueReset(samples);
}
