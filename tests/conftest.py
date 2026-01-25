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
_ha_mock.config_entries = MagicMock()
_ha_mock.config_entries.ConfigEntry = MagicMock()
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
_ha_mock.core = MagicMock()
_ha_mock.core.callback = lambda x: x
_ha_mock.core.Callable = MagicMock()
_ha_mock.exceptions = MagicMock()
_ha_mock.exceptions.HomeAssistantError = Exception
_ha_mock.helpers = MagicMock()
_ha_mock.helpers.device_registry = MagicMock()
_ha_mock.helpers.device_registry.CONNECTION_NETWORK_MAC = "mac"
_ha_mock.helpers.config_validation = MagicMock()
_ha_mock.helpers.dispatcher = MagicMock()
_ha_mock.helpers.typing = MagicMock()
_ha_mock.helpers.entity_registry = MagicMock()
_ha_mock.loader = MagicMock()
_ha_mock.loader.bind_hass = lambda x: x
_ha_mock.util = MagicMock()
_ha_mock.util.dt = MagicMock()
_ha_mock.util.logging = MagicMock()
_ha_mock.util.logging.catch_log_exception = lambda x, y: x
_ha_mock.components = MagicMock()
_ha_mock.components.mqtt = MagicMock()
_ha_mock.components.mqtt.Subscription = MagicMock()
_ha_mock.components.mqtt.models = MagicMock()

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
sys.modules["homeassistant.loader"] = _ha_mock.loader
sys.modules["homeassistant.util"] = _ha_mock.util
sys.modules["homeassistant.util.dt"] = _ha_mock.util.dt
sys.modules["homeassistant.util.logging"] = _ha_mock.util.logging
sys.modules["homeassistant.components"] = _ha_mock.components
sys.modules["homeassistant.components.mqtt"] = _ha_mock.components.mqtt
sys.modules["homeassistant.components.mqtt.models"] = _ha_mock.components.mqtt.models


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
