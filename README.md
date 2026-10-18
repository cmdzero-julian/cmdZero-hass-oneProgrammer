# ESP32 IR Blaster

A Home Assistant custom integration for a fleet of ESPHome-based ESP32 IR
senders and receivers: name and learn IR codes from a receiver, store them
centrally, and send any saved code to one or many sender devices from the
HA frontend.

It doesn't talk to the ESP32s directly — it rides on top of the stock
**ESPHome** integration, which must already have your devices added:

- **Sending** calls the `send_ir_code` API service each sender device
  already exposes.
- **Learning** listens for an `esphome.esp32_ir_code_captured` event fired
  by a receiver's `on_raw` handler (see `esphome/packages/ir_receiver.yaml`).

## Repo layout

- `custom_components/esp32_ir/` — the Home Assistant integration.
- `esphome/packages/` — shared ESPHome YAML for sender and receiver
  devices; `esphome/*.yaml` are the thin per-device files that include
  them via substitutions.

## Installing (manual, for now)

1. Copy `custom_components/esp32_ir` into your Home Assistant config's
   `custom_components/` directory (or symlink it while developing).
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "ESP32 IR Blaster".

Once this repo is pushed to GitHub, it can be added to
[HACS](https://hacs.xyz/) as a custom repository (HACS → the "⋮" menu →
Custom repositories → paste the repo URL, category "Integration"), which
gives you update notifications in the HACS UI — and a per-repository
"auto-update" toggle if you want updates applied without confirming each
time.

This repo is intended to stay **private** (it's just for us). HACS can
still pull from a private repo, but it needs a GitHub Personal Access
Token (classic, `repo` scope) configured under HACS → Settings →
"GitHub Personal Access Token" first — public custom repos don't need
this, private ones do.

## Usage

Services (Developer Tools → Actions, or from scripts/automations):

- `esp32_ir.learn_code` — arms the listener for the next IR code a
  receiver captures and saves it under a name. Point the remote at the
  receiver and press the button right after calling this.
- `esp32_ir.send_code` — sends a saved code to one or more sender devices.
- `esp32_ir.delete_code` — removes a saved code.
- `esp32_ir.list_codes` — returns all saved codes and their metadata.

A `select.esp32_ir_saved_codes` entity is also created, listing saved code
names, for building a dashboard dropdown without typing names into a
service call.

## Known limitations (v1)

- `learn_code` without a `receiver_device_id` captures the *next* IR event
  from *any* receiver — fine with a single active receiver, but worth
  revisiting once the combo sender/receiver field unit exists and more
  than one receiver might be listening at once.
- Resolving a device's ESPHome service name is done by slugifying its
  device registry name. This matches today because each device's
  `friendly_name` mirrors its `name`; if those ever diverge significantly
  for a device, service resolution for that device would need a look.
- No dedicated frontend panel yet — usage today is services + the one
  select entity. A proper visual code-picker/sender UI is a natural next
  step once this backend is proven out.
