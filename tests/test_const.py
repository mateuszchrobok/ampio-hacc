"""Tests for Ampio constants."""

from custom_components.ampio.const import (
    ALARM_CMD_ARM,
    ALARM_CMD_CLEAR,
    ALARM_CMD_DISARM,
    COVER_CMD_CLOSE,
    COVER_CMD_OPEN,
    COVER_CMD_STOP,
    COVER_MASK_BYTE,
    COVER_RAW_SET_POSITION,
    COVER_RAW_SET_TILT,
    COVER_TILT_CLOSED,
    COVER_TILT_KEEP_PREVIOUS,
    COVER_TILT_OPEN,
    DOMAIN,
    LIGHT_CMD_OFF,
    LIGHT_RGB_OFF,
    MSENS_PCB_V3,
    MSENS_PCB_V4,
    SWITCH_CMD_OFF,
    SWITCH_CMD_ON,
    ZONE_BITMASK,
)


class TestSwitchConstants:
    """Test switch command constants."""

    def test_switch_cmd_off(self):
        """Test switch off command is 0."""
        assert SWITCH_CMD_OFF == 0

    def test_switch_cmd_on(self):
        """Test switch on command is 1."""
        assert SWITCH_CMD_ON == 1


class TestCoverConstants:
    """Test cover command constants."""

    def test_cover_cmd_stop(self):
        """Test cover stop command is 0."""
        assert COVER_CMD_STOP == 0

    def test_cover_cmd_close(self):
        """Test cover close command is 1."""
        assert COVER_CMD_CLOSE == 1

    def test_cover_cmd_open(self):
        """Test cover open command is 2."""
        assert COVER_CMD_OPEN == 2

    def test_cover_raw_set_position(self):
        """Test cover raw position command prefix."""
        assert COVER_RAW_SET_POSITION == b"\x00\x01"

    def test_cover_raw_set_tilt(self):
        """Test cover raw tilt command prefix."""
        assert COVER_RAW_SET_TILT == b"\x00\x02"

    def test_cover_tilt_keep_previous(self):
        """Test cover tilt keep previous value."""
        assert COVER_TILT_KEEP_PREVIOUS == 0x66

    def test_cover_tilt_open(self):
        """Test cover tilt open value."""
        assert COVER_TILT_OPEN == 0x64  # 100 decimal

    def test_cover_tilt_closed(self):
        """Test cover tilt closed value."""
        assert COVER_TILT_CLOSED == 0x00


class TestAlarmConstants:
    """Test alarm command constants."""

    def test_alarm_cmd_arm(self):
        """Test alarm arm command prefix."""
        assert ALARM_CMD_ARM == "1E0080"

    def test_alarm_cmd_disarm(self):
        """Test alarm disarm command prefix."""
        assert ALARM_CMD_DISARM == "1E0084"

    def test_alarm_cmd_clear(self):
        """Test alarm clear command prefix."""
        assert ALARM_CMD_CLEAR == "1E0085"


class TestPCBVersionConstants:
    """Test PCB version constants."""

    def test_msens_pcb_v3(self):
        """Test MSENS PCB V3 constant."""
        assert MSENS_PCB_V3 == 3

    def test_msens_pcb_v4(self):
        """Test MSENS PCB V4 constant."""
        assert MSENS_PCB_V4 == 4


class TestLightConstants:
    """Test light command constants."""

    def test_light_cmd_off(self):
        """Test light off command is 0."""
        assert LIGHT_CMD_OFF == 0

    def test_light_rgb_off(self):
        """Test light RGB off command is 'off'."""
        assert LIGHT_RGB_OFF == "off"


class TestMaskConstants:
    """Test bitmask constants."""

    def test_zone_bitmask(self):
        """Test zone bitmask is 32-bit."""
        assert ZONE_BITMASK == 0xFFFFFFFF

    def test_cover_mask_byte(self):
        """Test cover mask byte is 8-bit."""
        assert COVER_MASK_BYTE == 0xFF


class TestDomainConstant:
    """Test domain constant."""

    def test_domain(self):
        """Test domain is 'ampio'."""
        assert DOMAIN == "ampio"
