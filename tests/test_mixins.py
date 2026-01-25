"""Tests for Ampio entity mixins."""

from custom_components.ampio.mixins import StateMessageMixin


class TestStateMessageMixin:
    """Test the StateMessageMixin class."""

    def test_parse_bool_state_true(self):
        """Test parsing boolean true state."""
        result = StateMessageMixin.parse_bool_state("1", "test")
        assert result is True

    def test_parse_bool_state_false(self):
        """Test parsing boolean false state."""
        result = StateMessageMixin.parse_bool_state("0", "test")
        assert result is False

    def test_parse_bool_state_invalid(self):
        """Test parsing invalid boolean state."""
        result = StateMessageMixin.parse_bool_state("invalid", "test")
        assert result is None

    def test_parse_bool_state_none(self):
        """Test parsing None boolean state."""
        result = StateMessageMixin.parse_bool_state(None, "test")
        assert result is None

    def test_parse_int_state_valid(self):
        """Test parsing valid integer state."""
        result = StateMessageMixin.parse_int_state("42", "test")
        assert result == 42

    def test_parse_int_state_negative(self):
        """Test parsing negative integer state."""
        result = StateMessageMixin.parse_int_state("-10", "test")
        assert result == -10

    def test_parse_int_state_invalid(self):
        """Test parsing invalid integer state."""
        result = StateMessageMixin.parse_int_state("not_a_number", "test")
        assert result is None

    def test_parse_int_state_min_valid(self):
        """Test parsing integer state within min bound."""
        result = StateMessageMixin.parse_int_state("5", "test", min_val=0)
        assert result == 5

    def test_parse_int_state_below_min(self):
        """Test parsing integer state below min bound."""
        result = StateMessageMixin.parse_int_state("-1", "test", min_val=0)
        assert result is None

    def test_parse_int_state_max_valid(self):
        """Test parsing integer state within max bound."""
        result = StateMessageMixin.parse_int_state("100", "test", max_val=255)
        assert result == 100

    def test_parse_int_state_above_max(self):
        """Test parsing integer state above max bound."""
        result = StateMessageMixin.parse_int_state("300", "test", max_val=255)
        assert result is None

    def test_parse_float_state_valid(self):
        """Test parsing valid float state."""
        result = StateMessageMixin.parse_float_state("21.5", "test")
        assert result == 21.5

    def test_parse_float_state_integer(self):
        """Test parsing integer as float state."""
        result = StateMessageMixin.parse_float_state("42", "test")
        assert result == 42.0

    def test_parse_float_state_negative(self):
        """Test parsing negative float state."""
        result = StateMessageMixin.parse_float_state("-10.5", "test")
        assert result == -10.5

    def test_parse_float_state_invalid(self):
        """Test parsing invalid float state."""
        result = StateMessageMixin.parse_float_state("not_a_float", "test")
        assert result is None

    def test_parse_rgb_state_valid(self):
        """Test parsing valid RGB state."""
        result = StateMessageMixin.parse_rgb_state("255,128,0", "test")
        assert result == (255, 128, 0)

    def test_parse_rgb_state_with_extra_values(self):
        """Test parsing RGB state with extra values (RGBW)."""
        result = StateMessageMixin.parse_rgb_state("255,128,0,255", "test")
        assert result == (255, 128, 0)

    def test_parse_rgb_state_insufficient_values(self):
        """Test parsing RGB state with insufficient values."""
        result = StateMessageMixin.parse_rgb_state("255,128", "test")
        assert result is None

    def test_parse_rgb_state_invalid(self):
        """Test parsing invalid RGB state."""
        result = StateMessageMixin.parse_rgb_state("not,rgb,values", "test")
        assert result is None

    def test_parse_rgb_state_empty(self):
        """Test parsing empty RGB state."""
        result = StateMessageMixin.parse_rgb_state("", "test")
        assert result is None

    def test_parse_rgbw_state_valid(self):
        """Test parsing valid RGBW state."""
        result = StateMessageMixin.parse_rgbw_state("255,128,0,64", "test")
        assert result == (255, 128, 0, 64)

    def test_parse_rgbw_state_insufficient_values(self):
        """Test parsing RGBW state with insufficient values."""
        result = StateMessageMixin.parse_rgbw_state("255,128,0", "test")
        assert result is None

    def test_parse_rgbw_state_invalid(self):
        """Test parsing invalid RGBW state."""
        result = StateMessageMixin.parse_rgbw_state("not,rgbw,values,here", "test")
        assert result is None
