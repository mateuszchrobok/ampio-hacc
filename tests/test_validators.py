"""Tests for validators module - standalone tests without Home Assistant."""

import sys
from unittest.mock import MagicMock

import pytest
import voluptuous as vol


# Mock homeassistant modules before importing validators
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.device_registry"] = MagicMock()


# Import the validator functions directly (validators.py only needs voluptuous)
from custom_components.ampio.validators import (
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
