"""Tests for validators module."""

import pytest
import voluptuous as vol

from custom_components.ampio.validators import (
    AMPIO_DESCRIPTION_SCHEMA,
    AMPIO_DESCRIPTIONS_SCHEMA,
    AMPIO_DEVICE_SCHEMA,
    AMPIO_DEVICES_SCHEMA,
    ensure_list,
    string,
)


class TestString:
    """Tests for string validator."""

    def test_string_with_string(self):
        """Test string with string input."""
        assert string("hello") == "hello"

    def test_string_with_int(self):
        """Test string with int input."""
        assert string(123) == "123"

    def test_string_with_float(self):
        """Test string with float input."""
        assert string(1.5) == "1.5"

    def test_string_with_none_raises(self):
        """Test string with None raises Invalid."""
        with pytest.raises(vol.Invalid, match="string value is None"):
            string(None)

    def test_string_with_list_raises(self):
        """Test string with list raises Invalid."""
        with pytest.raises(vol.Invalid, match="value should be a string"):
            string([1, 2, 3])

    def test_string_with_dict_raises(self):
        """Test string with dict raises Invalid."""
        with pytest.raises(vol.Invalid, match="value should be a string"):
            string({"key": "value"})


class TestEnsureList:
    """Tests for ensure_list validator."""

    def test_ensure_list_with_none(self):
        """Test ensure_list with None returns empty list."""
        assert ensure_list(None) == []

    def test_ensure_list_with_single_value(self):
        """Test ensure_list with single value wraps in list."""
        assert ensure_list("item") == ["item"]
        assert ensure_list(42) == [42]

    def test_ensure_list_with_list(self):
        """Test ensure_list with list returns same list."""
        original = [1, 2, 3]
        assert ensure_list(original) == original

    def test_ensure_list_with_empty_list(self):
        """Test ensure_list with empty list returns empty list."""
        assert ensure_list([]) == []


class TestAmpioDeviceSchema:
    """Tests for AMPIO_DEVICE_SCHEMA."""

    def test_valid_device(self):
        """Test schema with valid device data."""
        data = {
            "mac": "1B88",
            "user_mac": "AABB",
            "typ": 44,
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
            "name": "Test",
        }
        result = AMPIO_DEVICE_SCHEMA(data)
        assert result["mac"] == "1B88"
        assert result["typ"] == 44

    def test_missing_required_field(self):
        """Test schema raises on missing required field."""
        data = {"mac": "1B88"}  # Missing other required fields
        with pytest.raises(vol.MultipleInvalid):
            AMPIO_DEVICE_SCHEMA(data)


class TestAmpioDevicesSchema:
    """Tests for AMPIO_DEVICES_SCHEMA."""

    def test_valid_devices_list(self, sample_device_payload):
        """Test schema with valid devices list."""
        result = AMPIO_DEVICES_SCHEMA(sample_device_payload)
        assert result["s"] == 1
        assert len(result["d"]) == 1

    def test_empty_devices(self):
        """Test schema with empty devices list."""
        data = {"s": 0}
        result = AMPIO_DEVICES_SCHEMA(data)
        assert result["d"] == []

    def test_single_device_wrapped_in_list(self):
        """Test schema wraps single device in list."""
        data = {
            "s": 1,
            "d": {
                "mac": "1B88",
                "user_mac": "AABB",
                "typ": 44,
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
                "name": "Test",
            },
        }
        result = AMPIO_DEVICES_SCHEMA(data)
        assert isinstance(result["d"], list)
        assert len(result["d"]) == 1


class TestAmpioDescriptionSchema:
    """Tests for AMPIO_DESCRIPTION_SCHEMA."""

    def test_valid_description(self):
        """Test schema with valid description."""
        data = {
            "t": "t",
            "n": 1,
            "d": "VGVzdA==",  # "Test" in base64
        }
        result = AMPIO_DESCRIPTION_SCHEMA(data)
        assert result["t"] == "t"
        assert result["n"] == 1


class TestAmpioDescriptionsSchema:
    """Tests for AMPIO_DESCRIPTIONS_SCHEMA."""

    def test_valid_descriptions_list(self, sample_description_payload):
        """Test schema with valid descriptions list."""
        result = AMPIO_DESCRIPTIONS_SCHEMA(sample_description_payload)
        assert result["s"] == 1
        assert len(result["d"]) == 2

    def test_empty_descriptions(self):
        """Test schema with empty descriptions."""
        data = {"s": 0}
        result = AMPIO_DESCRIPTIONS_SCHEMA(data)
        assert result["d"] == []
