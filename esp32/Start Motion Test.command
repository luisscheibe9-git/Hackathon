#!/bin/zsh
cd -- "${0:A:h}"
/Users/anthonyouzounian/esp32-tools/venv/bin/python tools/csi_capture.py --test
printf '\nPress Enter to close.'
read
