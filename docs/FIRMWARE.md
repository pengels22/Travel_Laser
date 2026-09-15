# TS1 Firmware Inspection

Source inspected:

- File: `SCULPFUN TS1 v1.1.30.zip`
- Binary: `Sculpfun TS1 V1.1_V1.1.30_20240802.bin`
- Size: 8,327,168 bytes
- SHA-256: `779f20053a3ab733100e9802b77ca6005b4dd5cc37a64e5ecaee43a630ad7d2b`

The archive contains a single compiled ESP32 firmware image. It does not contain source code, schematics, release notes, or a readable manifest.

## Confirmed From Static Strings

- Firmware target is ESP32/Arduino based.
- Embedded build references include `esp32-arduino-lib-builder`.
- ESP-IDF reference string: `v3.3.5-1-g85c43024c`.
- Product strings include `Sculpfun TS1` and `Sculpfun TS1 V1.1`.
- Firmware/date-like string found: `2024080201`.
- Build hash-like string found: `9036908-dirty`.
- GRBL family string found: `Grbl_ESP32`.
- The firmware exposes standard GRBL status/error/alarm strings.
- The firmware includes Wi-Fi station/AP, HTTP, Telnet, mDNS, SPIFFS, and OTA/update related strings.
- The firmware includes strings for `Telnet/Port`, `Telnet/Enable`, `Http/Port`, `Http/Enable`, `System/Hostname`, `AP/SSID`, `AP/Password`, `Sta/SSID`, and `Sta/Password`.
- The firmware includes `/XY_UartToUSB.bin` and messages for starting an STM32 firmware update, suggesting the TS1 firmware package may bridge or update another controller component.

## Implications For This Retrofit

- The backend GRBL parser should continue to support normal GRBL/GRBL_ESP32 status lines, errors, and alarms.
- The project assumption that GRBL serial baud is `115200` remains the deployment default and is documented separately in hardware/config notes.
- TS1 firmware appears to have native Wi-Fi, HTTP, Telnet, and AP/STA concepts, but this retrofit should still keep the Orange Pi as the owner of Network mode and expose LightBurn through the Pi's TCP port `23`.
- The firmware strings reinforce that Wi-Fi credentials and web/Telnet settings may exist on the original TS1 controller, but they should not be confused with the Orange Pi's TS1 private AP and uplink Wi-Fi configuration.

## Still Not Answered By This Binary

- Exact USB VID/PID/serial for the laser controller as seen by Linux.
- Exact camera USB identity.
- Exact Orange Pi GPIO chip/line numbers.
- Runtime default Telnet port, HTTP port, hostname, SSID, or password values.
- TS1 display/touch pin mappings.
- Whether K1 causes USB disappearance or only interrupts motion/enable.

Use `scripts/identify-usb.sh`, Orange Pi pinout documentation, and live `gpioinfo`/USB inspection on the real hardware to resolve those items.
