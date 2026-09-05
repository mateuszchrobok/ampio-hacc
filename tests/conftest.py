"""Test fixtures for ampio-hacc.

This file sets up mocks for homeassistant modules BEFORE any test modules
are imported, allowing tests to import from custom_components.ampio.*
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock homeassistant modules BEFORE any imports from custom_components
# This must happen at module level, before pytest collects tests
_ha_mock = MagicMock()

# Config entries
_ha_mock.config_entries = MagicMock()
_ha_mock.config_entries.ConfigEntry = MagicMock()
_ha_mock.config_entries.ConfigFlow = MagicMock()

# Constants
_ha_mock.const = MagicMock()
_ha_mock.const.CONF_DEVICE = "device"
_ha_mock.const.CONF_DEVICE_CLASS = "device_class"
_ha_mock.const.CONF_FRIENDLY_NAME = "friendly_name"
_ha_mock.const.CONF_ICON = "icon"
_ha_mock.const.CONF_NAME = "name"
_ha_mock.const.CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"
_ha_mock.const.CONF_CLIENT_ID = "client_id"
_ha_mock.const.CONF_PASSWORD = "password"
_ha_mock.const.CONF_PORT = "port"
_ha_mock.const.CONF_USERNAME = "username"
_ha_mock.const.CONF_PROTOCOL = "protocol"
_ha_mock.const.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
_ha_mock.const.STATE_ON = "on"
_ha_mock.const.STATE_OFF = "off"

# Core
_ha_mock.core = MagicMock()
_ha_mock.core.callback = lambda x: x
_ha_mock.core.Callable = MagicMock()
_ha_mock.core.Event = MagicMock()
_ha_mock.core.HomeAssistant = MagicMock()

# Exceptions
_ha_mock.exceptions = MagicMock()
_ha_mock.exceptions.HomeAssistantError = Exception

# Helpers
_ha_mock.helpers = MagicMock()
_ha_mock.helpers.device_registry = MagicMock()
_ha_mock.helpers.device_registry.CONNECTION_NETWORK_MAC = "mac"
_ha_mock.helpers.config_validation = MagicMock()
_ha_mock.helpers.config_validation.string = lambda x: x
_ha_mock.helpers.config_validation.port = lambda x: x
_ha_mock.helpers.dispatcher = MagicMock()
_ha_mock.helpers.typing = MagicMock()
_ha_mock.helpers.entity_registry = MagicMock()
_ha_mock.helpers.entity = MagicMock()
_ha_mock.helpers.restore_state = MagicMock()
_ha_mock.helpers.update_coordinator = MagicMock()
_ha_mock.helpers.update_coordinator.DataUpdateCoordinator = MagicMock()
_ha_mock.helpers.update_coordinator.CoordinatorEntity = MagicMock()
_ha_mock.helpers.entity_platform = MagicMock()
_ha_mock.helpers.entity_platform.AddEntitiesCallback = MagicMock()

# Loader
_ha_mock.loader = MagicMock()
_ha_mock.loader.bind_hass = lambda x: x

# Util
_ha_mock.util = MagicMock()
_ha_mock.util.dt = MagicMock()
_ha_mock.util.logging = MagicMock()
_ha_mock.util.logging.catch_log_exception = lambda x, y: x

# Components - create a proper MagicMock that can be treated as a package
_components_mock = MagicMock()

# Alarm control panel component
_alarm_mock = MagicMock()
_alarm_mock.DOMAIN = "alarm_control_panel"
_alarm_mock.AlarmControlPanelEntity = MagicMock()
_components_mock.alarm_control_panel = _alarm_mock

# Binary sensor component
_binary_sensor_mock = MagicMock()
_binary_sensor_mock.DOMAIN = "binary_sensor"
_binary_sensor_mock.BinarySensorEntity = MagicMock()
_components_mock.binary_sensor = _binary_sensor_mock

# Cover component
_cover_mock = MagicMock()
_cover_mock.DOMAIN = "cover"
_cover_mock.CoverEntity = MagicMock()
_cover_mock.ATTR_POSITION = "position"
_cover_mock.ATTR_TILT_POSITION = "tilt_position"
_cover_mock.CoverDeviceClass = MagicMock()
_cover_mock.CoverEntityFeature = MagicMock()
_cover_mock.CoverEntityFeature.OPEN = 1
_cover_mock.CoverEntityFeature.CLOSE = 2
_cover_mock.CoverEntityFeature.SET_POSITION = 4
_cover_mock.CoverEntityFeature.STOP = 8
_cover_mock.CoverEntityFeature.SET_TILT_POSITION = 128
_components_mock.cover = _cover_mock

# Light component
_light_mock = MagicMock()
_light_mock.DOMAIN = "light"
_light_mock.LightEntity = MagicMock()
_light_mock.ATTR_BRIGHTNESS = "brightness"
_light_mock.ATTR_HS_COLOR = "hs_color"
_light_mock.ATTR_WHITE_VALUE = "white_value"
_light_mock.ColorMode = MagicMock()
_light_mock.ColorMode.BRIGHTNESS = "brightness"
_light_mock.ColorMode.HS = "hs"
_light_mock.ColorMode.RGBW = "rgbw"
_light_mock.LightEntityFeature = MagicMock()
_light_mock.LightEntityFeature.TRANSITION = 32
_components_mock.light = _light_mock

# Sensor component
_sensor_mock = MagicMock()
_sensor_mock.DOMAIN = "sensor"
_sensor_mock.SensorEntity = MagicMock()
_sensor_mock.SensorDeviceClass = MagicMock()
_sensor_mock.SensorStateClass = MagicMock()
_components_mock.sensor = _sensor_mock

# Number component
_number_mock = MagicMock()
_number_mock.DOMAIN = "number"
_number_mock.NumberEntity = MagicMock()
_number_mock.NumberEntityDescription = MagicMock()
_number_mock.NumberMode = MagicMock()
_number_mock.NumberMode.BOX = "box"
_number_mock.NumberMode.SLIDER = "slider"
_components_mock.number = _number_mock

# Switch component
_switch_mock = MagicMock()
_switch_mock.DOMAIN = "switch"
_switch_mock.SwitchEntity = MagicMock()
_components_mock.switch = _switch_mock

# Climate component
_climate_mock = MagicMock()
_climate_mock.DOMAIN = "climate"
_climate_mock.ClimateEntity = MagicMock()
_climate_mock.ClimateEntityFeature = MagicMock()
_climate_mock.ClimateEntityFeature.TARGET_TEMPERATURE = 1
_climate_mock.ClimateEntityFeature.PRESET_MODE = 16
_climate_mock.HVACMode = MagicMock()
_climate_mock.HVACMode.OFF = "off"
_climate_mock.HVACMode.HEAT = "heat"
_climate_mock.HVACMode.AUTO = "auto"
_climate_mock.HVACAction = MagicMock()
_climate_mock.HVACAction.OFF = "off"
_climate_mock.HVACAction.HEATING = "heating"
_climate_mock.HVACAction.IDLE = "idle"
_climate_mock.ATTR_TEMPERATURE = "temperature"
_climate_mock.ATTR_HVAC_MODE = "hvac_mode"
_components_mock.climate = _climate_mock

# Event component
_event_mock = MagicMock()
_event_mock.DOMAIN = "event"
_event_mock.EventEntity = MagicMock()
_event_mock.EventDeviceClass = MagicMock()
_event_mock.EventDeviceClass.BUTTON = "button"
_event_mock.EventDeviceClass.DOORBELL = "doorbell"
_event_mock.EventDeviceClass.MOTION = "motion"
_event_mock.EventEntityDescription = MagicMock()
_components_mock.event = _event_mock

# MQTT component
_mqtt_mock = MagicMock()
_mqtt_mock.Subscription = MagicMock()
_mqtt_mock.models = MagicMock()
_components_mock.mqtt = _mqtt_mock

_ha_mock.components = _components_mock

# Register all modules in sys.modules
sys.modules["homeassistant"] = _ha_mock
sys.modules["homeassistant.config_entries"] = _ha_mock.config_entries
sys.modules["homeassistant.const"] = _ha_mock.const
sys.modules["homeassistant.core"] = _ha_mock.core
sys.modules["homeassistant.exceptions"] = _ha_mock.exceptions
sys.modules["homeassistant.helpers"] = _ha_mock.helpers
sys.modules["homeassistant.helpers.device_registry"] = _ha_mock.helpers.device_registry
sys.modules["homeassistant.helpers.config_validation"] = _ha_mock.helpers.config_validation
sys.modules["homeassistant.helpers.dispatcher"] = _ha_mock.helpers.dispatcher
sys.modules["homeassistant.helpers.typing"] = _ha_mock.helpers.typing
sys.modules["homeassistant.helpers.entity_registry"] = _ha_mock.helpers.entity_registry
sys.modules["homeassistant.helpers.entity"] = _ha_mock.helpers.entity
sys.modules["homeassistant.helpers.restore_state"] = _ha_mock.helpers.restore_state
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_mock.helpers.update_coordinator
sys.modules["homeassistant.helpers.entity_platform"] = _ha_mock.helpers.entity_platform
sys.modules["homeassistant.loader"] = _ha_mock.loader
sys.modules["homeassistant.util"] = _ha_mock.util
sys.modules["homeassistant.util.dt"] = _ha_mock.util.dt
sys.modules["homeassistant.util.logging"] = _ha_mock.util.logging
sys.modules["homeassistant.components"] = _components_mock
sys.modules["homeassistant.components.alarm_control_panel"] = _alarm_mock
sys.modules["homeassistant.components.binary_sensor"] = _binary_sensor_mock
sys.modules["homeassistant.components.cover"] = _cover_mock
sys.modules["homeassistant.components.light"] = _light_mock
sys.modules["homeassistant.components.number"] = _number_mock
sys.modules["homeassistant.components.sensor"] = _sensor_mock
sys.modules["homeassistant.components.switch"] = _switch_mock
sys.modules["homeassistant.components.climate"] = _climate_mock
sys.modules["homeassistant.components.event"] = _event_mock
sys.modules["homeassistant.components.mqtt"] = _mqtt_mock
sys.modules["homeassistant.components.mqtt.models"] = _mqtt_mock.models


@pytest.fixture
def sample_device_payload():
    """Sample device list payload from Ampio server."""
    return {
        "s": 1,
        "d": [
            {
                "mac": "1B88",
                "user_mac": "AABB",
                "typ": 44,  # MSENS
                "pcb": 3,
                "soft_ver": 100,
                "protocol": 1,
                "date_prod": 20230101,
                "i": 8,
                "o": 4,
                "a": 2,
                "au": 1,
                "t": 1,
                "f": 16,
                "name": "VGVzdCBNb2R1bGU=",  # "Test Module" base64
            }
        ],
    }


@pytest.fixture
def sample_description_payload():
    """Sample description payload from Ampio server."""
    return {
        "s": 1,
        "d": [
            {
                "t": "t",
                "n": 1,
                "d": "VDpUZW1wZXJhdHVyZQ==",  # "T:Temperature" base64
            },
            {
                "t": "i",
                "n": 1,
                "d": "TTpNb3Rpb24=",  # "M:Motion" base64
            },
        ],
    }


# Import additional fixtures from fixtures module
