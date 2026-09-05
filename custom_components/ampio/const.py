"""Ampio platform constants."""

from __future__ import annotations

from typing import Final

from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_CONTROL_PANEL
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.event import DOMAIN as EVENT
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.number import DOMAIN as NUMBER
from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.components.switch import DOMAIN as SWITCH

DOMAIN: Final = "ampio"

COMPONENTS: Final = (
    ALARM_CONTROL_PANEL,
    BINARY_SENSOR,
    CLIMATE,
    COVER,
    EVENT,
    LIGHT,
    NUMBER,
    SENSOR,
    SWITCH,
)

# Configuration keys
CONF_BROKER: Final = "broker"

# Dispatcher signals
AMPIO_CONNECTED: Final = "ampio_connected"
AMPIO_DISCONNECTED: Final = "ampio_disconnected"
SIGNAL_ADD_ENTITIES: Final = "ampio_add_new_entities"
AMPIO_DISCOVERY_NEW: Final = "ampio_discovery_new_{}_{}"
AMPIO_DISCOVERY_UPDATED: Final = "ampio_discovery_updated"
AMPIO_MODULE_DISCOVERY_UPDATED: Final = "ampio_module_discovery_updated"

# Data storage keys
DATA_AMPIO: Final = "ampio"
DATA_AMPIO_COORDINATOR: Final = "coordinator"
DATA_AMPIO_MODULES: Final = "modules"
DATA_AMPIO_API: Final = "api"
DATA_AMPIO_CONFIG: Final = "config"
DATA_AMPIO_PLATFORM_LOADED: Final = "platform_loaded"
DATA_AMPIO_DISPATCHERS: Final = "dispatchers"
DATA_AMPIO_UNIQUE_IDS: Final = "unique_ids"
DATA_CONFIG_ENTRY_LOCK: Final = "ampio_config_entry_lock"
CONFIG_ENTRY_IS_SETUP: Final = "ampio_entry_is_setup"

# MQTT defaults
DEFAULT_DISCOVERY: Final = False
DEFAULT_QOS: Final = 0
DEFAULT_RETAIN: Final = False
DEFAULT_PORT: Final = 1883
DEFAULT_KEEPALIVE: Final = 60

# Protocol versions
PROTOCOL_31: Final = "3.1"
PROTOCOL_311: Final = "3.1.1"

# MQTT Topic patterns
TOPIC_PREFIX: Final = "ampio"
TOPIC_FROM: Final = f"{TOPIC_PREFIX}/from"
TOPIC_TO: Final = f"{TOPIC_PREFIX}/to"

# Version topics
TOPIC_VERSION_REQUEST: Final = f"{TOPIC_TO}/info/version"
TOPIC_VERSION_RESPONSE: Final = f"{TOPIC_FROM}/info/version"

# Discovery topics
TOPIC_DISCOVERY_REQUEST: Final = f"{TOPIC_TO}/can/dev/list"
TOPIC_DISCOVERY_RESPONSE: Final = f"{TOPIC_FROM}/can/dev/list"

# Module description topics
TOPIC_NAMES_REQUEST: Final = f"{TOPIC_TO}/{{mac}}/description"
TOPIC_NAMES_RESPONSE: Final = f"{TOPIC_FROM}/+/description"

# Entity configuration keys
CONF_STATE_TOPIC: Final = "state_topic"
CONF_COMMAND_TOPIC: Final = "command_topic"
CONF_BRIGHTNESS_STATE_TOPIC: Final = "brightness_state_topic"
CONF_BRIGHTNESS_COMMAND_TOPIC: Final = "brightness_command_topic"
CONF_UNIQUE_ID: Final = "unique_id"
CONF_DEVICE_INFO: Final = "device_info"
CONF_TILT_POSITION_TOPIC: Final = "tilt_position_topic"
CONF_CLOSING_STATE_TOPIC: Final = "cover_closing_state_topic"
CONF_OPENING_STATE_TOPIC: Final = "cover_opening_state_topic"
CONF_RAW_TOPIC: Final = "raw_topic"
CONF_RGB_STATE_TOPIC: Final = "rgb_state_topic"
CONF_RGB_COMMAND_TOPIC: Final = "rgb_command_topic"
CONF_WHITE_VALUE_STATE_TOPIC: Final = "white_state_topic"
CONF_WHITE_VALUE_COMMAND_TOPIC: Final = "white_command_topic"
CONF_ARMED_TOPIC: Final = "armed_topic"
CONF_ALARM_TOPIC: Final = "alarm_topic"
CONF_ENTRYTIME_TOPIC: Final = "entrytime_topic"
CONF_EXITTIME10_TOPIC: Final = "exittime10_topic"
CONF_EXITTIME_TOPIC: Final = "exittime_topic"
CONF_AWAY_ZONES: Final = "away_zones"
CONF_HOME_ZONES: Final = "home_zones"
CONF_MIN_VALUE: Final = "min_value"
CONF_MAX_VALUE: Final = "max_value"

# Attributes
ATTR_VERSION: Final = "version"
ATTR_DISCOVERY_PAYLOAD: Final = "discovery_payload"
ATTR_DEVICE_INFO: Final = "device_info"
ATTR_COMPONENT_CONFIGS: Final = "configs"

# Climate configuration keys
CONF_TEMPERATURE_STATE_TOPIC: Final = "temperature_state_topic"
CONF_SETPOINT_STATE_TOPIC: Final = "setpoint_state_topic"
CONF_SETPOINT_COMMAND_TOPIC: Final = "setpoint_command_topic"
CONF_MODE_STATE_TOPIC: Final = "mode_state_topic"
CONF_MODE_COMMAND_TOPIC: Final = "mode_command_topic"

# Ampio climate modes (rm register values)
AMPIO_CLIMATE_MODE_CALENDAR: Final = 0
AMPIO_CLIMATE_MODE_MANUAL_DAY: Final = 1
AMPIO_CLIMATE_MODE_MANUAL_NIGHT: Final = 2
AMPIO_CLIMATE_MODE_HOLIDAYS: Final = 3
AMPIO_CLIMATE_MODE_BLOCK: Final = 4

# Switch commands
SWITCH_CMD_OFF: Final = 0
SWITCH_CMD_ON: Final = 1

# Cover commands
COVER_CMD_STOP: Final = 0
COVER_CMD_CLOSE: Final = 1
COVER_CMD_OPEN: Final = 2
COVER_RAW_SET_POSITION: Final = b"\x00\x01"
COVER_RAW_SET_TILT: Final = b"\x00\x02"
COVER_TILT_KEEP_PREVIOUS: Final = 0x66
COVER_TILT_OPEN: Final = 0x64
COVER_TILT_CLOSED: Final = 0x00

# PCB version thresholds
MSENS_PCB_V3: Final = 3  # Standard M-SENS
MSENS_PCB_V4: Final = 4  # M-SENS-CO2

# Alarm raw command prefixes
ALARM_CMD_ARM: Final = "1E0080"
ALARM_CMD_DISARM: Final = "1E0084"
ALARM_CMD_CLEAR: Final = "1E0085"

# Light commands
LIGHT_CMD_OFF: Final = 0
LIGHT_RGB_OFF: Final = "off"

# Analog flag (afu8) commands.
#
# An 8-bit flag is NOT written the way a binary flag is. There is no
# ``ampio/to/<mac>/afu8/<n>/cmd`` topic: the value goes out as a raw CAN
# broadcast on ``ampio/to/<mac>/raw``, prefixed with this command id, then the
# value byte, then the 0-based flag index. Ampio's own Node-RED node builds
# exactly that frame (see ``node-red-contrib-ampio``, ``ampioin/out.js``, the
# ``valtype == 'afu8'`` branch), while every other writable type there falls
# through to the ``/cmd`` form.
ANALOG_FLAG_RAW_CMD: Final = b"\x7a\xf9"
ANALOG_FLAG_MIN: Final = 0
ANALOG_FLAG_MAX: Final = 255
ANALOG_FLAG_STEP: Final = 1

# Zone bitmask constants
ZONE_BITMASK: Final = 0xFFFFFFFF
COVER_MASK_BYTE: Final = 0xFF
