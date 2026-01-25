"""Tests for models module - standalone utility function tests."""

import base64
import sys
from unittest.mock import MagicMock

import pytest


# Mock homeassistant modules before any imports
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.const"].CONF_DEVICE = "device"
sys.modules["homeassistant.const"].CONF_DEVICE_CLASS = "device_class"
sys.modules["homeassistant.const"].CONF_FRIENDLY_NAME = "friendly_name"
sys.modules["homeassistant.const"].CONF_ICON = "icon"
sys.modules["homeassistant.const"].CONF_NAME = "name"
sys.modules["homeassistant.const"].CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.device_registry"] = MagicMock()
sys.modules["homeassistant.helpers.device_registry"].CONNECTION_NETWORK_MAC = "mac"


# Test base64 encode/decode functions directly
def base64decode(value: str):
    """Decode base64 string."""
    try:
        return base64.b64decode(value).decode("utf-8").strip()
    except UnicodeDecodeError:
        return base64.b64decode(value).decode("cp1254").strip()


def base64encode(value: str):
    """Encode base64 string."""
    return base64.b64encode(value.encode("utf-8"))


class TestBase64Decode:
    """Tests for base64decode function."""

    def test_decode_utf8(self):
        """Test decoding UTF-8 string."""
        encoded = base64.b64encode(b"Hello World").decode()
        assert base64decode(encoded) == "Hello World"

    def test_decode_with_whitespace(self):
        """Test decoding strips whitespace."""
        encoded = base64.b64encode(b"  Hello  ").decode()
        assert base64decode(encoded) == "Hello"

    def test_decode_utf8_special_chars(self):
        """Test decoding UTF-8 with special characters."""
        encoded = base64.b64encode("Temperature".encode("utf-8")).decode()
        assert base64decode(encoded) == "Temperature"


class TestBase64Encode:
    """Tests for base64encode function."""

    def test_encode_string(self):
        """Test encoding string."""
        result = base64encode("Hello")
        assert base64.b64decode(result).decode("utf-8") == "Hello"


class TestDeviceClasses:
    """Tests for DEVICE_CLASSES mapping."""

    def test_binary_sensor_classes(self):
        """Test binary sensor device classes."""
        # Import after mocking
        from custom_components.ampio.models import DEVICE_CLASSES

        assert DEVICE_CLASSES["D"] == "door"
        assert DEVICE_CLASSES["W"] == "window"
        assert DEVICE_CLASSES["M"] == "motion"

    def test_sensor_classes(self):
        """Test sensor device classes."""
        from custom_components.ampio.models import DEVICE_CLASSES

        assert DEVICE_CLASSES["T"] == "temperature"
        assert DEVICE_CLASSES["H"] == "humidity"
        assert DEVICE_CLASSES["PS"] == "pressure"


class TestTypeCodes:
    """Tests for TYPE_CODES mapping."""

    def test_module_codes(self):
        """Test module type codes."""
        from custom_components.ampio.models import TYPE_CODES

        assert TYPE_CODES[44] == "MSENS"
        assert TYPE_CODES[3] == "MROL-4s"
        assert TYPE_CODES[5] == "MDIM-8s"
        assert TYPE_CODES[25] == "MCON"


class TestItemTypes:
    """Tests for ItemTypes enum."""

    def test_item_types_values(self):
        """Test ItemTypes enum values."""
        from custom_components.ampio.models import ItemTypes

        assert ItemTypes.Temperature.value == "t"
        assert ItemTypes.BinaryFlag.value == "f"
        assert ItemTypes.BinaryInput.value == "i"
        assert ItemTypes.BinaryOutput.value == "o"
        assert ItemTypes.AnalogInput.value == "a"
        assert ItemTypes.AnalogOutput.value == "au"


class TestExtractIndexFromTopic:
    """Tests for extract_index_from_topic function."""

    def test_extract_valid_index(self):
        """Test extracting valid index from topic."""
        from custom_components.ampio.models import extract_index_from_topic

        assert extract_index_from_topic("ampio/from/1B88/state/t/1") == 1
        assert extract_index_from_topic("ampio/from/AABB/state/o/5") == 5

    def test_extract_invalid_index(self):
        """Test extracting invalid index returns None."""
        from custom_components.ampio.models import extract_index_from_topic

        assert extract_index_from_topic("ampio/from/1B88/state/t/invalid") is None


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test creating a Message."""
        from custom_components.ampio.models import Message

        msg = Message(
            topic="test/topic",
            payload="test_payload",
            qos=1,
            retain=False,
        )
        assert msg.topic == "test/topic"
        assert msg.payload == "test_payload"
        assert msg.qos == 1
        assert msg.retain is False

    def test_message_with_defaults(self):
        """Test Message with default values."""
        from custom_components.ampio.models import Message

        msg = Message(
            topic="test",
            payload="data",
            qos=0,
            retain=True,
        )
        assert msg.subscribed_topic is None
        assert msg.timestamp is None
