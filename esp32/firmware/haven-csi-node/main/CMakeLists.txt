idf_component_register(
    SRCS "main.c" "node_config.c" "csi.c" "stream.c" "motion.c" "led.c"
    INCLUDE_DIRS "."
    REQUIRES esp_wifi esp_netif esp_event nvs_flash esp_timer lwip mbedtls esp_driver_gpio esp_app_format
)
