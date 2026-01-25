"""Tests for models module."""

import base64

import pytest

from custom_components.ampio.models import (
    DEVICE_CLASSES,
    TYPE_CODES,
    AmpioModuleInfo,
    IndexIntData,
    ItemName,
    ItemTypes,
    Message,
    base64decode,
    base64encode,
    extract_index_from_topic,
)


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


class TestExtractIndexFromTopic:
    """Tests for extract_index_from_topic function."""

    def test_extract_valid_index(self):
        """Test extracting valid index from topic."""
        assert extract_index_from_topic("ampio/from/1B88/state/t/1") == 1
        assert extract_index_from_topic("ampio/from/AABB/state/o/5") == 5

    def test_extract_invalid_index(self):
        """Test extracting invalid index returns None."""
        assert extract_index_from_topic("ampio/from/1B88/state/t/invalid") is None


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test creating a Message."""
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
        msg = Message(
            topic="test",
            payload="data",
            qos=0,
            retain=True,
        )
        assert msg.subscribed_topic is None
        assert msg.timestamp is None


class TestIndexIntData:
    """Tests for IndexIntData class."""

    def test_from_msg_valid(self):
        """Test creating IndexIntData from valid message."""
        msg = Message(
            topic="ampio/from/1B88/state/t/5",
            payload="42",
            qos=0,
            retain=False,
        )
        result = IndexIntData.from_msg(msg)
        assert result is not None
        assert result.index == 5
        assert result.value == 42

    def test_from_msg_invalid_index(self):
        """Test from_msg with invalid index returns None."""
        msg = Message(
            topic="ampio/from/1B88/state/t/invalid",
            payload="42",
            qos=0,
            retain=False,
        )
        result = IndexIntData.from_msg(msg)
        assert result is None

    def test_from_msg_invalid_payload(self):
        """Test from_msg with invalid payload returns None."""
        msg = Message(
            topic="ampio/from/1B88/state/t/5",
            payload="not_a_number",
            qos=0,
            retain=False,
        )
        result = IndexIntData.from_msg(msg)
        assert result is None


class TestItemTypes:
    """Tests for ItemTypes enum."""

    def test_item_types_values(self):
        """Test ItemTypes enum values."""
        assert ItemTypes.Temperature.value == "t"
        assert ItemTypes.BinaryFlag.value == "f"
        assert ItemTypes.BinaryInput.value == "i"
        assert ItemTypes.BinaryOutput.value == "o"
        assert ItemTypes.AnalogInput.value == "a"
        assert ItemTypes.AnalogOutput.value == "au"


class TestDeviceClasses:
    """Tests for DEVICE_CLASSES mapping."""

    def test_binary_sensor_classes(self):
        """Test binary sensor device classes."""
        assert DEVICE_CLASSES["D"] == "door"
        assert DEVICE_CLASSES["W"] == "window"
        assert DEVICE_CLASSES["M"] == "motion"

    def test_sensor_classes(self):
        """Test sensor device classes."""
        assert DEVICE_CLASSES["T"] == "temperature"
        assert DEVICE_CLASSES["H"] == "humidity"
        assert DEVICE_CLASSES["PS"] == "pressure"


class TestTypeCodes:
    """Tests for TYPE_CODES mapping."""

    def test_module_codes(self):
        """Test module type codes."""
        assert TYPE_CODES[44] == "MSENS"
        assert TYPE_CODES[3] == "MROL-4s"
        assert TYPE_CODES[5] == "MDIM-8s"
        assert TYPE_CODES[25] == "MCON"


class TestItemName:
    """Tests for ItemName class."""

    def test_name_without_prefix(self):
        """Test ItemName without device class prefix."""
        encoded = base64encode("Simple Name")
        item = ItemName(encoded)
        assert item.name == "Simple Name"
        assert item.device_class is None
        assert item.prefix is None

    def test_name_with_prefix(self):
        """Test ItemName with device class prefix."""
        encoded = base64encode("T:Temperature Sensor")
        item = ItemName(encoded)
        assert item.name == "Temperature Sensor"
        assert item.device_class == "temperature"
        assert item.prefix == "T"

    def test_name_with_door_prefix(self):
        """Test ItemName with door device class."""
        encoded = base64encode("D:Front Door")
        item = ItemName(encoded)
        assert item.name == "Front Door"
        assert item.device_class == "door"
        assert item.prefix == "D"

    def test_name_with_unknown_prefix(self):
        """Test ItemName with unknown prefix."""
        encoded = base64encode("XX:Unknown Type")
        item = ItemName(encoded)
        assert item.name == "Unknown Type"
        assert item.device_class is None
        assert item.prefix == "XX"

    def test_from_topic_payload(self, sample_description_payload):
        """Test creating ItemNames from topic payload."""
        result = ItemName.from_topic_payload(sample_description_payload)
        assert "t" in result
        assert "i" in result
        assert 1 in result["t"]
        assert result["t"][1].device_class == "temperature"


class TestAmpioModuleInfo:
    """Tests for AmpioModuleInfo class."""

    def test_from_topic_payload(self, sample_device_payload):
        """Test creating modules from topic payload."""
        modules = AmpioModuleInfo.from_topic_payload(sample_device_payload)
        assert len(modules) == 1
        module = modules[0]
        assert module.mac == "1B88"
        assert module.user_mac == "AABB"
        assert module.code == 44

    def test_part_number(self, sample_device_payload):
        """Test part_number property."""
        modules = AmpioModuleInfo.from_topic_payload(sample_device_payload)
        module = modules[0]
        assert module.part_number == "MSENS"

    def test_model_property(self, sample_device_payload):
        """Test model property."""
        modules = AmpioModuleInfo.from_topic_payload(sample_device_payload)
        module = modules[0]
        assert "MSENS" in module.model
        assert "1B88" in module.model
        assert "AABB" in module.model

    def test_as_hass_device(self, sample_device_payload):
        """Test as_hass_device returns correct format."""
        modules = AmpioModuleInfo.from_topic_payload(sample_device_payload)
        module = modules[0]
        device_info = module.as_hass_device()

        assert "identifiers" in device_info
        assert "name" in device_info
        assert device_info["manufacturer"] == "Ampio"
        assert "sw_version" in device_info

    def test_mac_uppercase_conversion(self, sample_device_payload):
        """Test MAC addresses are converted to uppercase."""
        payload = sample_device_payload.copy()
        payload["d"][0]["mac"] = "1b88"  # lowercase
        payload["d"][0]["user_mac"] = "aabb"  # lowercase

        modules = AmpioModuleInfo.from_topic_payload(payload)
        module = modules[0]
        assert module.mac == "1B88"
        assert module.user_mac == "AABB"
