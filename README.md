# ESPHome Components (RP2040 Focused)

[![ESPHome Compile](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml)

## Build Status by Version

| Version | Status |
|---------|--------|
| `2026.2.1` | [![2026.2.1 (latest)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml) |
| `2026.2.0` | [![2026.2.0](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-2026.2.0)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-2026.2.0) |
| `2026.1.5` | [![2026.1.5](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-2026.1.5)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-2026.1.5) |
| `2026.1.4` | [![2026.1.4](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-2026.1.4)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-2026.1.4) |
| `2026.1.3` | [![2026.1.3](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-2026.1.3)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-2026.1.3) |
| `2026.1.2` | [![2026.1.2](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-2026.1.2)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-2026.1.2) |
| `2026.1.1` | [![2026.1.1](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-2026.1.1)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-2026.1.1) |
| `2026.1.0` | [![2026.1.0](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-2026.1.0)](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-2026.1.0) |

A small collection of custom **ESPHome external components** for use in your ESPHome projects.

I run most of my ESPHome devices with RP2040 / PicoW boards. However they do not seem to get the same attention from ESPHome compared to ESP modules...

Currently included:

- **`dht`** – DHT sensor support (example: DHT22 on RP2040 / Pico W)
- **`mqtt`** – MQTT component setup for RP2040/Pico W using async libraries

---

## Install / Use in ESPHome

Add this to your ESPHome YAML:

```yaml
external_components:
  - source: github://zet-root/esphome-components@main
    components: [ dht, mqtt ]
```

I publish my fixes for some versions of ESPHome only, so please make sure to be on that version to have a working patch!

```yaml
external_components:
  - source: github://zet-root/esphome-components@zet-2026.1.1
    components: [ dht, mqtt ]
```

See [.versions.yml](.versions.yml) for all tested ESPHome versions and the latest stable version.

---

## Component: `dht`

Minimal example for **DHT22** on **Raspberry Pi Pico W (RP2040)**.  
This example also includes an `absolute_humidity` sensor derived from the DHT readings.

I added a fix for my DHT sensor, so it would work with a RP2040. I even tried to upstream this: https://github.com/esphome/esphome/issues/10364

[Minimal DHT Example Yaml](config/minimal-dht.yaml)

### Notes
- `INPUT_PULLUP` enables an internal pull-up resistor on the data pin.
- Adjust `update_interval` to fit your needs.
- Ensure your DHT sensor wiring is correct (power, ground, data pin). On the PicoW this can be used to solder a 4-wire Sensor directly onto the Pin, such that GND, VCC and Data aligns. I have this always on pin, cause it is my VCC.

---

## Component: `mqtt`

Minimal example MQTT configuration for **Pico W (RP2040)** using async networking libraries.

MQTT is missing in ESPHome as of now, for the RP2040. So I tried to make that happen for the newest version. It is not as complex as you would think.

[Minimal MQTT Example Yaml](config/minimal-mqtt.yaml)

### Notes
- Replace `192.168.x.x` with your broker IP/hostname.
- `birth_message` and `will_message` are useful for availability / LWT style monitoring.

---

## Development

PRs and issues are welcome. If you add a new component, consider including:
- a minimal YAML example
- any required libraries / `platformio_options`
- tested boards / chipsets

### Testing

To test components locally:

1. **Set up ESPHome** at a specific version (or use the one from `.versions.yml`):
   ```bash
   git clone https://github.com/esphome/esphome.git
   cd esphome
   git checkout 2026.1.1  # Or any supported version from .versions.yml
   pip install -e .
   cd ..
   ```

2. **Create a config with secrets**:
   ```bash
   cat > secrets.yaml <<EOF
   wifi_ssid: "test"
   wifi_password: "test-password"
   EOF
   ```

3. **Compile a minimal example**:
   ```bash
   esphome compile config/minimal-dht.yaml
   esphome compile config/minimal-mqtt.yaml
   ```

The GitHub Actions workflow (`.github/workflows/esphome-compile.yml`) automatically tests against all supported versions on every push to main. See the [workflow results](https://github.com/zet-root/esphome-components/actions/workflows/esphome-compile.yml) for details.
