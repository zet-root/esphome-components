# Vendored RP2040 libraries

`AsyncMqttClient-esphome` (heman, 2.0.0) and `AsyncTCP_RP2040W` (khoih-prog,
1.2.0) as published on the PlatformIO registry, plus the patch below. The mqtt
component adds them for `rp2` builds as `symlink://` libraries, so they come
with the component checkout and need no extra setup on the Home Assistant
ESPHome add-on. Both keep their LGPL-3.0 licence.

## Why

arduino-pico runs lwIP in `PICO_CYW43_ARCH_THREADSAFE_BACKGROUND` mode: lwIP
callbacks run from a low-priority IRQ. arduino-pico wraps every lwIP entry point
with `LWIPMutex` (`-Wl,--wrap=tcp_write` and friends), so a single lwIP call is
safe, but nothing stops the IRQ from running *between* two calls of the sketch:

- `AsyncMqttClient::publish()` writes one MQTT packet as several
  `AsyncClient::add()` calls plus one `send()`. A keepalive ping (`_onPoll`) or
  an ack (`_onData`) from the IRQ lands in the middle of that sequence. The
  broker reads a malformed frame and closes the socket ("Disconnected: TCP
  disconnected" every few minutes on the pm42 energy meter).
- A disconnect from the IRQ (`_s_error` → `_pcb = NULL`) between those calls
  makes `send()` call `tcp_output(NULL)`. lwIP asserts, pico-sdk `panic()`s and
  the board reboots (crash dump: `panic` ← `tcp_output`, reset reason
  "Crash (HardFault)"). The `SEMAPHORE_TAKE/GIVE` macros that guard this on
  ESP32 were no-ops on RP2040.

## What changed

- `AsyncMqttClient.hpp`: `SEMAPHORE_TAKE()` is an `LWIPMutex` guard on RP2040,
  held until the packet is written. The lock is recursive and the IRQ defers
  while it is held; deferred work runs when the outermost guard is released.
- `AsyncTCP_RP2040W.cpp`: `send()` returns `false` instead of calling lwIP with
  a NULL pcb; `add()`, `send()`, `close()`, `abort()`, `free()`, `connected()`
  and `space()` hold `LWIPMutex` for their whole body.
- `library.json`: versions `+zet.1`; AsyncMqttClient's ESP8266/ESP32
  dependencies dropped (this copy is only used on RP2040).

Diff against the registry releases: `git log -- components/mqtt/lib`.
