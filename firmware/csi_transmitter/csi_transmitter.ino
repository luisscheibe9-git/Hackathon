#include <WiFi.h>
#include <WiFiUdp.h>

WiFiUDP traffic;
const IPAddress broadcast(192, 168, 4, 255);

void setup() {
  Serial.begin(115200);
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP("Stillpoint-CSI", "stillpoint-demo", 6)) {
    Serial.println("Failed to start Stillpoint-CSI");
    return;
  }
  traffic.begin(50000);
  Serial.println("Stillpoint-CSI transmitting on channel 6 when receivers join");
}

void loop() {
  if (WiFi.softAPgetStationNum() > 0) {
    traffic.beginPacket(broadcast, 50000);
    traffic.write(reinterpret_cast<const uint8_t *>("CSI"), 3);
    traffic.endPacket();
  }
  delay(30);
}
