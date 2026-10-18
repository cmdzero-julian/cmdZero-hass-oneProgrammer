"""Constants for the ESP32 IR Blaster integration."""

DOMAIN = "esp32_ir"

# Must match the `event:` value fired by packages/ir_receiver.yaml.
# ESPHome only allows HA events prefixed with "esphome.".
EVENT_CODE_CAPTURED = "esphome.esp32_ir_code_captured"

STORAGE_KEY = f"{DOMAIN}_codes"
STORAGE_VERSION = 1

SERVICE_LEARN_CODE = "learn_code"
SERVICE_SEND_CODE = "send_code"
SERVICE_DELETE_CODE = "delete_code"
SERVICE_LIST_CODES = "list_codes"

CONF_NAME = "name"
CONF_RECEIVER_DEVICE_ID = "receiver_device_id"
CONF_TIMEOUT = "timeout"
CONF_OVERWRITE = "overwrite"
CONF_TARGETS = "targets"

DEFAULT_LEARN_TIMEOUT = 10

SIGNAL_CODES_UPDATED = f"{DOMAIN}_codes_updated"
