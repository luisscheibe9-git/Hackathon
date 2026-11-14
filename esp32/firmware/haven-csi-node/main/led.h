/** Status LED (GPIO 2 on most ESP32-WROOM-32U dev boards; set in menuconfig).
 *  no settings: double blink | connecting: fast blink | streaming: blinks node id, pause | no CSI: slow blink */
#pragma once

typedef enum { LED_NO_CONFIG, LED_CONNECTING, LED_STREAMING, LED_NO_CSI } led_state_t;

void led_init(int node_id);
void led_set(led_state_t s);
