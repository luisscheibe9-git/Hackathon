#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_wifi.h>
#include <esp_wifi_ap_get_sta_list.h>

WiFiUDP traffic;
wifi_sta_mac_ip_list_t receivers = {};
unsigned long lastRefresh = 0;
bool started = false;

void setup() {
  Serial.begin(115200);
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP("Stillpoint-CSI", "stillpoint-demo", 6)) {
    Serial.println("Failed to start Stillpoint-CSI");
    return;
  }
  esp_wifi_set_bandwidth(WIFI_IF_AP, WIFI_BW_HT20);
  started = traffic.begin(50000);
  Serial.println("Stillpoint-CSI transmitting on channel 6 when receivers join");
}

void loop() {
  if (started && traffic.parsePacket() > 0) {
    uint8_t packet[16];
    const int size = traffic.read(packet, sizeof(packet));
    if (size > 0 && traffic.beginPacket(traffic.remoteIP(), traffic.remotePort())) {
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
  for (int i = 0; i < receivers.num; ++i) {
    const uint32_t address = receivers.sta[i].ip.addr;
    if (address && traffic.beginPacket(IPAddress(address), 50000)) {
      traffic.write(reinterpret_cast<const uint8_t *>("CSI"), 3);
      traffic.endPacket();
    }
  }
  delay(30);
}
