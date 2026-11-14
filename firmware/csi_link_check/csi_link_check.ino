#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_wifi.h>
#include <atomic>

std::atomic<unsigned long> frames{0};
uint8_t accessPoint[6];
QueueHandle_t samples;
const char *standaloneSsid = "Stillpoint-CSI";

struct CsiSample {
  uint32_t timestamp;
  int8_t rssi;
  bool firstWordInvalid;
  uint8_t data[128];
};

void onCsi(void *, wifi_csi_info_t *info) {
  if (info && info->buf && info->len >= sizeof(CsiSample::data) &&
      memcmp(info->mac, accessPoint, 6) == 0) {
    frames.fetch_add(1, std::memory_order_relaxed);
    CsiSample sample{info->rx_ctrl.timestamp, info->rx_ctrl.rssi, info->first_word_invalid, {}};
    memcpy(sample.data, info->buf, sizeof(sample.data));
    xQueueSend(samples, &sample, 0);
  }
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
  const bool standalone = ssid == standaloneSsid;
  WiFiUDP probe;
  uint8_t relay[136] = {'C'};
  if (standalone) {
    probe.begin(50001);
    esp_wifi_get_mac(WIFI_IF_STA, relay + 1);
  }
  while (WiFi.status() == WL_CONNECTED) {
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
        relay[7] = static_cast<uint8_t>(sample.rssi);
        memcpy(relay + 8, sample.data, sizeof(sample.data));
        if (probe.beginPacket(WiFi.gatewayIP(), 50000)) {
          probe.write(relay, sizeof(relay));
          probe.endPacket();
        }
      }
      if (!configuredOverUsb) {
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
  xQueueReset(samples);
}
