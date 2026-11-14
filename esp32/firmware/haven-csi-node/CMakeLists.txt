# Haven CSI node firmware for classic ESP32 (ESP32-WROOM-32U and other ESP32-D0WD boards).
# Requires ESP-IDF v5.4 or newer.
cmake_minimum_required(VERSION 3.16)
set(PROJECT_VER "0.1.0")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(haven-csi-node)
