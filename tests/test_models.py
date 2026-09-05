"""Tests for models module."""

import base64

import pytest

from custom_components.ampio.models import (
    CLASS_FACTORY,
    DEVICE_CLASSES,
    TYPE_CODES,
    AmpioAnalogFlag8Config,
    AmpioModuleInfo,
    IndexIntData,
    ItemName,
    ItemTypes,
    Message,
    analog_flag_raw_payload,
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
        encoded = base64.b64encode(b"Temperature").decode()
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


class TestAnalogFlagRawPayload:
    """Tests for the afu8 raw CAN payload encoder.

    The reference is Ampio's own Node-RED node (node-red-contrib-ampio,
    ampioin/out.js): for valtype 'afu8' it publishes to ampio/to/<mac>/raw with
    '7AF9' + hex(value) + hex(ioid - 1). These cases assert that exact frame.
    """

    def test_command_prefix(self):
        """Test the frame starts with the 7af9 command id."""
        assert analog_flag_raw_payload(0, 1).startswith("7af9")

    def test_value_then_zero_based_index(self):
        """Test value comes first and the index is decremented."""
        # vendor: '7AF9' + (255).toString(16) + (1-1).toString(16).padStart(2,'0')
        assert analog_flag_raw_payload(255, 1) == "7af9ff00"

    def test_single_hex_digits_are_zero_padded(self):
        """Test both bytes are two hex digits even when the value is small."""
        assert analog_flag_raw_payload(5, 2) == "7af90501"

    def test_high_index(self):
        """Test an index above 16 encodes as one byte."""
        assert analog_flag_raw_payload(64, 18) == "7af94011"

    def test_minimum(self):
        """Test writing zero."""
        assert analog_flag_raw_payload(0, 1) == "7af90000"

    def test_payload_is_four_bytes(self):
        """Test the frame is always 4 bytes of ASCII hex."""
        assert len(analog_flag_raw_payload(200, 9)) == 8

    def test_value_above_range_raises(self):
        """Test an out-of-range value is refused, not truncated."""
        with pytest.raises(ValueError, match="outside 0-255"):
            analog_flag_raw_payload(256, 1)

    def test_negative_value_raises(self):
        """Test a negative value is refused."""
        with pytest.raises(ValueError, match="outside 0-255"):
            analog_flag_raw_payload(-1, 1)

    def test_zero_index_raises(self):
        """Test a 0-based index passed in by mistake is refused."""
        with pytest.raises(ValueError, match="index 0 outside"):
            analog_flag_raw_payload(1, 0)

    def test_index_above_range_raises(self):
        """Test an index that will not fit in one byte is refused."""
        with pytest.raises(ValueError, match="outside 1-256"):
            analog_flag_raw_payload(1, 257)


def _module(code: int = 22, **names) -> AmpioModuleInfo:
    """Build a module info carrying the given names map."""
    module = AmpioModuleInfo(
        mac="1b88",
        user_mac="85da",
        code=code,
        pcb=1,
        software=100,
        protocol=22,
        date_prod="20230101",
        i=8,
        o=8,
        a=0,
        au=0,
        t=0,
        flags=16,
        name=base64encode("Test Module"),
    )
    module.names = names
    return module


class TestAmpioAnalogFlag8Config:
    """Tests for the afu8 entity config."""

    def test_topics_and_identity(self):
        """Test the state topic, raw topic and unique id."""
        item = ItemName(base64encode("Tryb pracy"))
        config = AmpioAnalogFlag8Config.from_ampio_device(_module(), item, 3).config

        assert config["state_topic"] == "ampio/from/85DA/state/afu8/3"
        assert config["raw_topic"] == "ampio/to/85DA/raw"
        assert config["unique_id"] == "ampio-85DA-afu8-3"
        assert config["friendly_name"] == "Tryb pracy"

    def test_no_command_topic(self):
        """Test no per-item command topic is offered - afu8 has none."""
        item = ItemName(base64encode("Tryb pracy"))
        config = AmpioAnalogFlag8Config.from_ampio_device(_module(), item, 3).config

        assert "command_topic" not in config

    def test_defaults_to_full_byte_range(self):
        """Test an unbounded project object gets the register's own range."""
        item = ItemName(base64encode("Tryb pracy"))
        config = AmpioAnalogFlag8Config.from_ampio_device(_module(), item, 1).config

        assert config["min_value"] == 0
        assert config["max_value"] == 255

    def test_project_bounds_win(self):
        """Test the project's own min/max are preferred when usable."""
        item = ItemName(base64encode("Tryb pracy"), value_min=0, value_max=4)
        config = AmpioAnalogFlag8Config.from_ampio_device(_module(), item, 1).config

        assert config["min_value"] == 0
        assert config["max_value"] == 4

    def test_inverted_project_bounds_are_rejected(self):
        """Test min >= max falls back rather than producing an unusable entity."""
        item = ItemName(base64encode("Tryb pracy"), value_min=10, value_max=10)
        config = AmpioAnalogFlag8Config.from_ampio_device(_module(), item, 1).config

        assert (config["min_value"], config["max_value"]) == (0, 255)

    def test_out_of_byte_project_bounds_are_rejected(self):
        """Test bounds outside 0-255 cannot come from a one-byte register."""
        item = ItemName(base64encode("Tryb pracy"), value_min=0, value_max=1000)
        config = AmpioAnalogFlag8Config.from_ampio_device(_module(), item, 1).config

        assert (config["min_value"], config["max_value"]) == (0, 255)

    def test_falls_back_to_a_generated_name(self):
        """Test an empty label still yields something identifiable."""
        item = ItemName(base64encode(""))
        config = AmpioAnalogFlag8Config.from_ampio_device(_module(), item, 7).config

        assert config["friendly_name"] == "Flag 8-bit 7 Test Module"


class TestUpdateConfigsAnalogFlag:
    """Tests that discovery turns afu8 names into number entities."""

    def test_afu8_names_become_number_configs(self):
        """Test each afu8 name yields one number config."""
        module = _module(
            **{
                ItemTypes.AnalogFlag8: {
                    3: ItemName(base64encode("Tryb pracy")),
                    18: ItemName(base64encode("Scena")),
                }
            }
        )
        module.update_configs()

        numbers = module.get_config_for_component("number")
        assert len(numbers) == 2
        assert {c["unique_id"] for c in numbers} == {
            "ampio-85DA-afu8-3",
            "ampio-85DA-afu8-18",
        }
        assert module.unique_ids >= {"ampio-85DA-afu8-3", "ampio-85DA-afu8-18"}

    def test_no_afu8_names_means_no_number_configs(self):
        """Test modules without 8-bit flags gain nothing."""
        module = _module(**{ItemTypes.BinaryFlag: {1: ItemName(base64encode("Flaga"))}})
        module.update_configs()

        assert module.get_config_for_component("number") == []
        assert len(module.get_config_for_component("switch")) == 1

    def test_afu8_does_not_collide_with_binary_flags(self):
        """Test an afu8 and an f at the same index are separate entities."""
        module = _module(
            **{
                ItemTypes.BinaryFlag: {1: ItemName(base64encode("Flaga"))},
                ItemTypes.AnalogFlag8: {1: ItemName(base64encode("Tryb"))},
            }
        )
        module.update_configs()

        assert module.get_config_for_component("number")[0]["unique_id"] == "ampio-85DA-afu8-1"
        assert module.get_config_for_component("switch")[0]["unique_id"] == "ampio-85DA-f1"
        assert len(module.unique_ids) == 2


def _mcon(software: int, **names) -> AmpioModuleInfo:
    """Build an M-CON (type 25) carrying the given names map.

    ``software`` decides everything: ``% 100 == 1`` is the INTEGRA build that
    bridges a Satel panel, anything else is an M-CON doing an unrelated job.
    """
    module = CLASS_FACTORY[25](
        mac="7fa9",
        user_mac="7fa9",
        code=25,
        pcb=1,
        software=software,
        protocol=22,
        date_prod="20230101",
        i=0,
        o=0,
        a=0,
        au=0,
        t=0,
        flags=0,
        name=base64encode("A170: Satel"),
    )
    module.names = names
    return module


class TestSatelZoneDiscovery:
    """Tests that an M-CON's Satel zones become binary sensors."""

    def test_satel_input_is_its_own_topic_type(self):
        """Test the item type is the topic segment, not a variant of i."""
        assert ItemTypes.SatelInput.value == "bi"
        assert ItemTypes.BinaryInput.value == "i"

    def test_integra_zones_become_binary_sensors(self):
        """Test each named zone yields one binary sensor on state/bi/<n>."""
        module = _mcon(
            3001,
            **{
                ItemTypes.SatelInput: {
                    1: ItemName(base64encode("PIR Wejście")),
                    20: ItemName(base64encode("kDrzwiLazParter")),
                }
            },
        )
        module.update_configs()

        sensors = module.get_config_for_component("binary_sensor")
        assert [c["unique_id"] for c in sensors] == ["ampio-7FA9-bi1", "ampio-7FA9-bi20"]
        assert [c["state_topic"] for c in sensors] == [
            "ampio/from/7FA9/state/bi/1",
            "ampio/from/7FA9/state/bi/20",
        ]
        assert [c["friendly_name"] for c in sensors] == ["PIR Wejście", "kDrzwiLazParter"]

    def test_zone_names_carry_no_device_class_by_default(self):
        """Test a plain project name yields a generic on/off sensor.

        Nothing on the wire says whether a zone is a motion detector, a door reed
        or a tamper loop, and the project's own name is free text -- "PIR Salon"
        is a convention of one installer, not a protocol. The prefix mechanism
        (``M:PIR Salon``) stays the only way to declare one.
        """
        module = _mcon(3001, **{ItemTypes.SatelInput: {6: ItemName(base64encode("PIR Salon"))}})
        module.update_configs()

        assert "device_class" not in module.get_config_for_component("binary_sensor")[0]

    def test_device_class_prefix_is_still_honoured(self):
        """Test an installer who does declare a class gets it."""
        module = _mcon(3001, **{ItemTypes.SatelInput: {6: ItemName(base64encode("M:PIR Salon"))}})
        module.update_configs()

        config = module.get_config_for_component("binary_sensor")[0]
        assert config["device_class"] == "motion"
        assert config["friendly_name"] == "PIR Salon"

    def test_non_integra_mcon_gets_no_zones(self):
        """Test zone rows on a serial-master M-CON create nothing.

        A project allocates ``satel_wej`` rows on every M-CON, including the ones
        wired to a heat pump or an air conditioner. Those modules never publish
        ``state/bi/<n>``, so an entity there would sit at ``unknown`` forever.
        """
        module = _mcon(7007, **{ItemTypes.SatelInput: {1: ItemName(base64encode("PIR Wejście"))}})
        module.update_configs()

        assert module.get_config_for_component("binary_sensor") == []
        assert module.get_config_for_component("alarm_control_panel") == []

    def test_no_zones_means_no_binary_sensors(self):
        """Test an INTEGRA bridge with no named zones still gains nothing."""
        module = _mcon(3001)
        module.update_configs()

        assert module.get_config_for_component("binary_sensor") == []
        assert len(module.get_config_for_component("alarm_control_panel")) == 1

    def test_project_zone_wins_over_a_legacy_handshake_name(self):
        """Test one index yields one entity when both name sources have it.

        Both routes end on ``state/bi/<n>`` and share a unique id. The project
        database is the live source; the description handshake is dead.
        """
        module = _mcon(
            3001,
            **{
                ItemTypes.BinaryInput: {1: ItemName(base64encode("Stara nazwa"))},
                ItemTypes.SatelInput: {1: ItemName(base64encode("PIR Wejście"))},
            },
        )
        module.update_configs()

        sensors = module.get_config_for_component("binary_sensor")
        assert len(sensors) == 1
        assert sensors[0]["friendly_name"] == "PIR Wejście"

    def test_legacy_handshake_names_alone_still_work(self):
        """Test the pre-existing i-to-bi mapping is untouched."""
        module = _mcon(3001, **{ItemTypes.BinaryInput: {4: ItemName(base64encode("Strefa 4"))}})
        module.update_configs()

        sensors = module.get_config_for_component("binary_sensor")
        assert len(sensors) == 1
        assert sensors[0]["state_topic"] == "ampio/from/7FA9/state/bi/4"
