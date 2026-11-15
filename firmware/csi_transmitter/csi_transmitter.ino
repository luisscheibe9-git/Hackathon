#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_wifi.h>
#include <esp_wifi_ap_get_sta_list.h>

WiFiUDP traffic;
wifi_sta_mac_ip_list_t receivers = {};
unsigned long lastRefresh = 0;
unsigned long lastTransmit = 0;
bool started = false;

void setup() {
  Serial.begin(460800);
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP("Stillpoint-CSI", "stillpoint-demo", 6)) {
    Serial.println("Failed to start Stillpoint-CSI, rebooting");
    delay(1000);
    ESP.restart();  // demo self-recovery: retry from a clean boot instead of sitting dead
  }
  // Demo self-recovery: if loop() ever hangs for ~5 s, the chip resets itself. Receivers #2/#3
  // notice the silence and reboot too (see csi_link_check.ino), so the whole set rejoins alone.
  enableLoopWDT();
  esp_wifi_set_bandwidth(WIFI_IF_AP, WIFI_BW_HT20);
  started = traffic.begin(50000);
  Serial.println("Stillpoint-CSI transmitting on channel 6 when receivers join");
}

void loop() {
  if (started && traffic.parsePacket() > 0) {
    uint8_t packet[136];
    const int size = traffic.read(packet, sizeof(packet));
    if (size == sizeof(packet) && (packet[0] == 'C' || packet[0] == 'P')) {
      const char digits[] = "0123456789abcdef";
      char hex[257];
      for (size_t i = 0; i < 128; ++i) {
        hex[i * 2] = digits[packet[i + 8] >> 4];
        hex[i * 2 + 1] = digits[packet[i + 8] & 15];
      }
      hex[256] = '\0';
      Serial.printf("%s,%02x%02x%02x%02x%02x%02x,%d,%s\n",
                    packet[0] == 'P' ? "PEER" : "RELAY",
                    packet[1], packet[2], packet[3], packet[4], packet[5], packet[6],
                    static_cast<int8_t>(packet[7]), hex);
    } else if (size == 3 && memcmp(packet, "CSI", 3) == 0 &&
               traffic.beginPacket(traffic.remoteIP(), traffic.remotePort())) {
      traffic.write(packet, size);
      traffic.endPacket();
    }
  }
  if (started && millis() - lastRefresh >= 1000) {
    lastRefresh = millis();
    wifi_sta_list_t stations = {};
    receivers.num = 0;
    if (esp_wifi_ap_get_sta_list(&stations) == ESP_OK) {
      esp_wifi_ap_get_sta_list_with_ip(&stations, &receivers);
    }
  }
  if (millis() - lastTransmit >= 30) {
    lastTransmit = millis();
    for (int i = 0; i < receivers.num; ++i) {
      const uint32_t address = receivers.sta[i].ip.addr;
      if (address && traffic.beginPacket(IPAddress(address), 50000)) {
        traffic.write(reinterpret_cast<const uint8_t *>("CSI"), 3);
        traffic.endPacket();
      }
    }
  }
  delay(2);
}
