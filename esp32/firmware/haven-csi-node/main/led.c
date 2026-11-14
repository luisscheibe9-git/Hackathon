#include "led.h"

#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

static volatile led_state_t s_state = LED_CONNECTING;
static int s_node;

static void out(int on)
{
#if CONFIG_HAVEN_LED_GPIO >= 0
    gpio_set_level(CONFIG_HAVEN_LED_GPIO, CONFIG_HAVEN_LED_ACTIVE_HIGH ? on : !on);
#endif
}

static void pulse(int on_ms, int off_ms)
{
    out(1);
    vTaskDelay(pdMS_TO_TICKS(on_ms));
    out(0);
    vTaskDelay(pdMS_TO_TICKS(off_ms));
}

static void led_task(void *arg)
{
    (void)arg;
    for (;;) {
        switch (s_state) {
        case LED_NO_CONFIG: pulse(80, 120); pulse(80, 1200); break;
        case LED_CONNECTING: pulse(100, 100); break;
        case LED_NO_CSI: pulse(500, 500); break;
        case LED_STREAMING:
            for (int i = 0; i < (s_node > 0 && s_node < 10 ? s_node : 1); i++) pulse(120, 250);
            vTaskDelay(pdMS_TO_TICKS(1800));
            break;
        }
    }
}

void led_init(int node_id)
{
    s_node = node_id;
#if CONFIG_HAVEN_LED_GPIO >= 0
    gpio_reset_pin(CONFIG_HAVEN_LED_GPIO);
    gpio_set_direction(CONFIG_HAVEN_LED_GPIO, GPIO_MODE_OUTPUT);
    out(0);
    xTaskCreate(led_task, "led", 2048, NULL, 1, NULL);
#endif
}

void led_set(led_state_t s)
{
    s_state = s;
}
