"""Ampio data models."""

from __future__ import annotations

import base64
import datetime as dt
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, ClassVar

from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
    CONF_ICON,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.helpers import device_registry

from .const import (
    CONF_ALARM_TOPIC,
    CONF_ARMED_TOPIC,
    CONF_AWAY_ZONES,
    CONF_BRIGHTNESS_COMMAND_TOPIC,
    CONF_BRIGHTNESS_STATE_TOPIC,
    CONF_CLOSING_STATE_TOPIC,
    CONF_COMMAND_TOPIC,
    CONF_ENTRYTIME_TOPIC,
    CONF_EXITTIME10_TOPIC,
    CONF_EXITTIME_TOPIC,
    CONF_HOME_ZONES,
    CONF_MODE_COMMAND_TOPIC,
    CONF_MODE_STATE_TOPIC,
    CONF_OPENING_STATE_TOPIC,
    CONF_RAW_TOPIC,
    CONF_RGB_COMMAND_TOPIC,
    CONF_RGB_STATE_TOPIC,
    CONF_SETPOINT_COMMAND_TOPIC,
    CONF_SETPOINT_STATE_TOPIC,
    CONF_STATE_TOPIC,
    CONF_TEMPERATURE_STATE_TOPIC,
    CONF_TILT_POSITION_TOPIC,
    CONF_UNIQUE_ID,
    CONF_WHITE_VALUE_COMMAND_TOPIC,
    CONF_WHITE_VALUE_STATE_TOPIC,
    DOMAIN,
    MSENS_PCB_V3,
    MSENS_PCB_V4,
)
from .validators import (
    AMPIO_DESCRIPTIONS_SCHEMA,
    AMPIO_DEVICES_SCHEMA,
    ATTR_A,
    ATTR_AU,
    ATTR_D,
    ATTR_DATE_PROD,
    ATTR_DEVICES,
    ATTR_FLAG,
    ATTR_I,
    ATTR_MAC,
    ATTR_N,
    ATTR_NAME,
    ATTR_O,
    ATTR_PCB,
    ATTR_PROTOCOL,
    ATTR_SOFTWARE,
    ATTR_T,
    ATTR_TYPE,
    ATTR_USERMAC,
)

DEVICE_CLASSES: dict[str, str] = {
    "B": "battery",
    "BC": "battery_charging",
    "C": "cold",
    "CO": "connectivity",
    "D": "door",
    "GD": "garage_door",
    "GA": "gas",
    "HE": "heat",
    "L": "light",
    "LO": "lock",
    "MI": "moisture",
    "M": "motion",
    "MV": "moving",
    "OC": "occupancy",
    "O": "opening",
    "P": "plug",
    "PW": "power",
    "PR": "presence",
    "PB": "problem",
    "S": "safety",
    "SO": "sound",
    "V": "vibration",
    "W": "window",
    # switches
    "OU": "outlet",
    # sensors
    "T": "temperature",
    "H": "humidity",
    "I": "illuminance",
    "SS": "signal_strength",
    "PS": "pressure",
    "TS": "timestamp",
    # covers
    "VA": "valve",
    "G": "garage",
    "BL": "blind",
}

TYPE_CODES: dict[int, str] = {
    # Touch panels
    6: "MDOT-6",
    8: "MDOT-4",
    11: "MDOT-9",
    18: "MDOT-18",
    27: "MDOT-15LCD",
    33: "MDOT-2",
    # Sensors
    44: "MSENS",
    45: "MSENS-LITE",
    34: "METEO-1s",
    # Roller/Cover
    3: "MROL-4s",
    # Relay modules
    4: "MPR-8s",
    7: "MREL-2s",
    9: "MREL-10s",
    # Dimmer modules
    5: "MDIM-8s",
    13: "MDIM-1p",
    14: "MDIM-2s",
    # Server/Control
    10: "MSERV-3s",
    # RGB/LED
    12: "MRGBu-1",
    17: "MLED-1",
    19: "MLED-s",
    # Climate/Heating
    22: "MRT-16s",
    23: "MRT-s",
    # RUPS - Relay Unit Power Sockets
    24: "RUPS",
    # Integration modules
    25: "MCON",
    28: "MCON-232-s",
    29: "MCON-485-s",
    30: "MCON-DL-s",
    31: "MCON-IR",
    32: "MCON-HVAC-p",
    # Output modules
    26: "MOC-4",
    35: "MOC-8s",
    36: "MOC-32s",
    # Input modules
    37: "MIN-8s",
    39: "MIN-16s",
    40: "MIN-2p",
    41: "MIN-11p",
    42: "MIN-AD8s",
    43: "MIN-IMP4s",
    46: "MIN-TCD3p",
    47: "MIN-AC4s",
    # Combo input/output modules
    48: "MINOC-4p",
    50: "MINOC-8s",
    # Analog output
    51: "MOUT-4s",
    52: "MOUT-4p",
    # Other
    38: "MRDN-1s",
    49: "MWRC",
    53: "MALARM-8s",
    54: "MAV-AMP-s",
    55: "MRDN-5s",
    69: "MKIN-MULTI",  # Multi-function module (Kinetic/Chorus/IAQ/Rekuperator)
    # Wireless
    56: "WL-REL-2p",
    57: "WL-REL-ROL1p",
    58: "WL-OC-RGBW1p",
    59: "WZ-SENS-TMP-p",
}


class ModuleCodes(IntEnum):
    """Module codes enum."""

    MLED1 = 17
    MCON = 25
    MDIM8s = 5
    MSENS = 44
    MDOT2 = 33


_LOGGER = logging.getLogger(__name__)

PublishPayloadType = str | bytes | int | float | None


@dataclass(frozen=True, slots=True)
class Message:
    """MQTT Message."""

    topic: str
    payload: PublishPayloadType
    qos: int
    retain: bool
    subscribed_topic: str | None = None
    timestamp: dt.datetime | None = None


MessageCallbackType = Callable[[Message], None]


def extract_index_from_topic(topic: str) -> int | None:
    """Take last part of topic as number."""
    parts = topic.split("/")
    try:
        return int(parts[-1])
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class IndexIntData:
    """Represents the index from last part of topic with data."""

    index: int
    value: int

    @classmethod
    def from_msg(cls, msg: Message) -> IndexIntData | None:
        """Create from MQTT message."""
        index = extract_index_from_topic(msg.topic)
        if index is None:
            _LOGGER.error("Unable to extract index from topic: %s", msg.topic)
            return None

        try:
            payload_str = (
                msg.payload.decode() if isinstance(msg.payload, bytes) else str(msg.payload)
            )
            value = int(payload_str)
        except (ValueError, TypeError, AttributeError):
            _LOGGER.error("Unable to parse data message tp ind: %s", msg.payload)
            return None
        return cls(index, value)


class ItemTypes(str, Enum):
    """Item type codes."""

    Temperature = "t"
    BinaryFlag = "f"
    BinaryInput = "i"
    BinaryOutput = "o"
    AnalogInput = "a"
    AnalogOutput = "au"
    # Extended analog types
    AnalogOutput16 = "au16"  # 16-bit unsigned (0-65536)
    AnalogOutput16L = "au16l"  # 16-bit unsigned reduced by 10K (0-6553.6)
    AnalogOutput32 = "au32"  # 32-bit unsigned
    AnalogFlag8 = "afu8"  # 8-bit flags (0-255)
    AnalogFlag16 = "afi16"  # 16-bit signed flags (-32768 to 32767)
    # RGB types
    RGB = "rgb"
    RGBW = "rgbw"
    # Climate/setpoint types
    Setpoint = "rs"  # Temperature setpoint (-99.9 to 155.0)
    SetpointDayNight = "rsdn"  # Day/Night setpoints
    Mode = "rm"  # Operating mode (0-4)


def base64decode(value: str) -> str:
    """Decode base64 string."""
    try:
        return base64.b64decode(value).decode("utf-8").strip()
    except UnicodeDecodeError:
        return base64.b64decode(value).decode("cp1254").strip()


def base64encode(value: str) -> str:
    """Encode string to base64 string."""
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


@dataclass
class ItemName:
    """Name of the ampio module Item (input, output, flag, etc)."""

    d: str  # Raw base64 encoded data
    name: str = field(init=False)
    device_class: str | None = field(init=False)
    prefix: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Initialize computed fields after dataclass init."""
        # Decode the base64 data
        decoded = base64decode(self.d)
        self.d = decoded

        # Extract name
        parts = decoded.split(":")
        if len(parts) > 1:
            self.name = "".join(parts[1:])
        else:
            self.name = decoded

        # Extract device_class
        if len(parts) > 1:
            prefix = parts[0]
            self.device_class = DEVICE_CLASSES.get(prefix)
        else:
            self.device_class = None

        # Extract prefix
        if len(parts) > 1:
            self.prefix = parts[0]
        else:
            self.prefix = None

    @classmethod
    def from_topic_payload(cls, payload: dict[str, Any]) -> dict[str, dict[int, ItemName]]:
        """Read from topic payload."""
        names: dict[str, Any] = AMPIO_DESCRIPTIONS_SCHEMA(payload)
        result: dict[str, dict[int, ItemName]] = {}
        for name in names[ATTR_D]:
            name_data = name[ATTR_D]
            name_type = name[ATTR_T]
            name_index = name[ATTR_N]
            if name_type not in result:
                result[name_type] = {}
            result[name_type][name_index] = ItemName(name_data)
        return result


@dataclass
class AmpioModuleInfo:
    """Ampio Module Information."""

    mac: str
    user_mac: str
    code: int
    pcb: int
    software: int
    protocol: int
    date_prod: str
    i: int
    o: int
    a: int
    au: int
    t: int
    flags: int
    name: str

    names: dict[str, Any] = field(default_factory=dict)
    configs: dict[str, list[Any]] = field(default_factory=dict)
    unique_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Convert mac addresses to uppercase and decode name."""
        self.mac = self.mac.upper()
        self.user_mac = self.user_mac.upper()
        self.name = base64decode(self.name)

    def update_configs(self) -> None:
        """Update the config data for entities."""
        self.configs = defaultdict(list)  # clean up current configs
        self.unique_ids = set()
        for index, item in self.names.get(ItemTypes.BinaryFlag, {}).items():
            flag_data = AmpioFlagConfig.from_ampio_device(self, item, index + 1)
            if flag_data and flag_data.unique_id:
                self.configs["switch"].append(flag_data.config)
                self.unique_ids.add(flag_data.unique_id)

        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            temp_data = AmpioTempSensorConfig.from_ampio_device(self, item, index + 1)
            if temp_data and temp_data.unique_id:
                self.configs["sensor"].append(temp_data.config)
                self.unique_ids.add(temp_data.unique_id)

    @property
    def part_number(self) -> str | int:
        """Return module part number (code)."""
        return TYPE_CODES.get(self.code, self.code)

    @property
    def model(self) -> str:
        """Return model name."""
        return f"{self.part_number} [{self.mac.upper()}/{self.user_mac.upper()}]"

    def as_hass_device(self) -> dict[str, Any]:
        """Return info in hass device format."""
        return {
            "connections": {(device_registry.CONNECTION_NETWORK_MAC, self.user_mac)},
            "identifiers": {(DOMAIN, self.user_mac)},
            "name": self.name,
            "manufacturer": "Ampio",
            "model": self.model,
            "sw_version": self.software,
            "via_device": (DOMAIN, "ampio-mqtt"),
        }

    @classmethod
    def from_topic_payload(cls, payload: dict[str, Any]) -> list[AmpioModuleInfo]:
        """Create a module object from topic payload."""
        devices = AMPIO_DEVICES_SCHEMA(payload)
        result: list[AmpioModuleInfo] = []
        # Support both old format (d) and new format (devices)
        device_list = devices.get(ATTR_D) or devices.get(ATTR_DEVICES, [])
        for device in device_list:
            # Use GenericModuleInfo for unknown module types (provides auto-detection)
            # Note: GenericModuleInfo is defined later in the file but is in CLASS_FACTORY
            klass = CLASS_FACTORY.get(device[ATTR_TYPE])
            if klass is None:
                # Import GenericModuleInfo dynamically to avoid forward reference issues
                klass = CLASS_FACTORY.get(-1, AmpioModuleInfo)  # -1 is reserved for generic
            result.append(
                klass(
                    mac=device[ATTR_MAC],
                    user_mac=device[ATTR_USERMAC],
                    code=device[ATTR_TYPE],
                    pcb=device[ATTR_PCB],
                    software=device[ATTR_SOFTWARE],
                    protocol=device[ATTR_PROTOCOL],
                    date_prod=device[ATTR_DATE_PROD],
                    i=device[ATTR_I],
                    o=device[ATTR_O],
                    a=device[ATTR_A],
                    au=device[ATTR_AU],
                    t=device[ATTR_T],
                    flags=device[ATTR_FLAG],
                    name=device[ATTR_NAME],
                )
            )
        return result

    def get_config_for_component(self, component: str) -> list[Any]:
        """Return list of entities for specific component."""
        return self.configs.get(component, [])


class MSENSModuleInfo(AmpioModuleInfo):
    """MSENS Ampio module information.

    M-SENS variants:
    - PCB < MSENS_PCB_V3: M-SENS-1 (basic, temperature only via au32)
    - PCB == MSENS_PCB_V3: M-SENS (standard, T/H/P/Noise/Illuminance/AQ)
    - PCB >= MSENS_PCB_V4: M-SENS-CO2 (adds CO2 sensor at au16l/7)
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        sensor_configs: list[AmpioConfig | None] = [
            AmpioTempSensorConfig.from_ampio_device(self, ItemName(base64encode("T:Temperature"))),
            AmpioHumiditySensorConfig.from_ampio_device(
                self, ItemName(base64encode("HU:Humidity"))
            ),
            AmpioPressureSensorConfig.from_ampio_device(
                self, ItemName(base64encode("OS:Pressure"))
            ),
            AmpioNoiseSensorConfig.from_ampio_device(self, ItemName(base64encode("SS:Noise"))),
            AmpioIlluminanceSensorConfig.from_ampio_device(
                self, ItemName(base64encode("I:Illuminance"))
            ),
            AmpioAirqualitySensorConfig.from_ampio_device(
                self, ItemName(base64encode("Air Quality"))
            ),
        ]

        # Add CO2 sensor for M-SENS-CO2 variant (PCB >= MSENS_PCB_V4)
        if self.pcb >= MSENS_PCB_V4:
            sensor_configs.append(
                AmpioCO2SensorConfig.from_ampio_device(
                    self, ItemName(base64encode("CO2:Carbon Dioxide"))
                )
            )

        for ampio_config in sensor_configs:
            if ampio_config and ampio_config.unique_id:
                self.configs["sensor"].append(ampio_config.config)
                self.unique_ids.add(ampio_config.unique_id)


class MCONModuleInfo(AmpioModuleInfo):
    """MCON Ampio module information."""

    def update_configs(self) -> None:
        """Update config."""
        super().update_configs()
        if self.software % 100 == 1:  # INTEGRA
            for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
                binary_data = AmpioBinarySensorExtendedConfig.from_ampio_device(self, item, index)
                if binary_data and binary_data.unique_id:
                    self.configs["binary_sensor"].append(binary_data.config)
                    self.unique_ids.add(binary_data.unique_id)

            satel_data = AmpioSatelConfig.from_ampio_device(self)
            if satel_data and satel_data.unique_id:
                self.configs["alarm_control_panel"].append(satel_data.config)
                self.unique_ids.add(satel_data.unique_id)


class MCON232sModuleInfo(AmpioModuleInfo):
    """MCON-232-s: RS-232 serial integration module.

    Provides binary inputs and outputs for serial device integration.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create binary sensors for inputs
        for index in range(1, self.i + 1):
            item = self.names.get(ItemTypes.BinaryInput, {}).get(index)
            if item is None:
                item = ItemName(base64encode(f"Input {index}"))

            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)

        # Create switches for outputs
        for index in range(1, self.o + 1):
            item = self.names.get(ItemTypes.BinaryOutput, {}).get(index)
            if item is None:
                item = ItemName(base64encode(f"Output {index}"))

            # Check if it should be a light (L: prefix) or switch
            if item.device_class == "light":
                light_data = AmpioLightConfig.from_ampio_device(self, item, index)
                if light_data and light_data.unique_id:
                    self.configs["light"].append(light_data.config)
                    self.unique_ids.add(light_data.unique_id)
            else:
                switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
                if switch_data and switch_data.unique_id:
                    self.configs["switch"].append(switch_data.config)
                    self.unique_ids.add(switch_data.unique_id)


class MCON485sModuleInfo(MCON232sModuleInfo):
    """MCON-485-s: RS-485 serial integration module.

    Same functionality as MCON-232-s but with RS-485 interface.
    """


class MCONDLsModuleInfo(AmpioModuleInfo):
    """MCON-DL-s: DALI lighting control module.

    Provides DALI bus control for lighting fixtures.
    Creates light entities for DALI outputs.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # DALI outputs as dimmable lights
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


class MCONIRModuleInfo(AmpioModuleInfo):
    """MCON-IR: Infrared control module.

    Provides IR transmitter control for A/V equipment.
    Creates switch entities for IR commands.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # IR outputs as switches
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
            if switch_data and switch_data.unique_id:
                self.configs["switch"].append(switch_data.config)
                self.unique_ids.add(switch_data.unique_id)


class MCONHVACpModuleInfo(AmpioModuleInfo):
    """MCON-HVAC-p: HVAC integration module.

    Provides integration with HVAC systems.
    Creates climate and sensor entities.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Temperature sensors
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            sensor_data = AmpioTempSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)

        # Control outputs as switches
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
            if switch_data and switch_data.unique_id:
                self.configs["switch"].append(switch_data.config)
                self.unique_ids.add(switch_data.unique_id)


class MLED1ModuleInfo(AmpioModuleInfo):
    """MLED-1 Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()
        _LOGGER.debug("MLED1: %s", self.names)
        for index, item in self.names.get(ItemTypes.AnalogOutput.value, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


class MDIM8sModuleInfo(AmpioModuleInfo):
    """MDIM-8s Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()
        _LOGGER.debug("MDIM8s: %s", self.names)

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


class MOC4ModuleInfo(AmpioModuleInfo):
    """MOC-4 Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()
        _LOGGER.debug("MOC4: %s", self.names)
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


class MPR8sModuleInfo(AmpioModuleInfo):
    """MPR-8s Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            if item.device_class == "light":
                light_data = AmpioLightConfig.from_ampio_device(self, item, index)
                if light_data.unique_id:
                    self.configs["light"].append(light_data.config)
                    self.unique_ids.add(light_data.unique_id)
            else:
                switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
                if switch_data.unique_id:
                    self.configs["switch"].append(switch_data.config)
                    self.unique_ids.add(switch_data.unique_id)

        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)


class MDOTModuleInfo(AmpioModuleInfo):
    """Generic MDOT Ampio module information class."""

    _BUTTONS: ClassVar[int] = 0

    def update_configs(self) -> None:
        """Generate module configuration."""
        super().update_configs()
        for index in range(
            1, self._BUTTONS + 1
        ):  # regardless of names module has always fixed physical touch buttons
            item = self.names.get(ItemTypes.BinaryInput, {}).get(index)
            if item is None:
                item = ItemName(base64encode(f"{self.name} Button {index}"))
            # Create binary sensor for backwards compatibility
            touch_data = AmpioTouchSensorConfig.from_ampio_device(self, item, index)
            if touch_data and touch_data.unique_id:
                self.configs["binary_sensor"].append(touch_data.config)
                self.unique_ids.add(touch_data.unique_id)
            # Also create event entity for button press/release events
            event_data = AmpioEventConfig.from_ampio_device(self, item, index)
            if event_data and event_data.unique_id:
                self.configs["event"].append(event_data.config)
                self.unique_ids.add(event_data.unique_id)


class MDOT2ModuleInfo(MDOTModuleInfo):
    """MDOT-2 Ampio module information."""

    _BUTTONS: ClassVar[int] = 2


class MDOT4ModuleInfo(MDOTModuleInfo):
    """MDOT-4 Ampio module information."""

    _BUTTONS: ClassVar[int] = 4


class MDOT9ModuleInfo(MDOTModuleInfo):
    """MDOT-9 Ampio module information."""

    _BUTTONS: ClassVar[int] = 9


class MDOT15LCDModuleInfo(MDOTModuleInfo):
    """MDOT-15LCD Ampio module information."""

    _BUTTONS: ClassVar[int] = 15


class MRGBu1ModuleInfo(AmpioModuleInfo):
    """MRGB-1u Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()
        rgb_data = AmpioRGBLightConfig.from_ampio_device(self, None, 1)
        if rgb_data and rgb_data.unique_id:
            self.configs["light"].append(rgb_data.config)
            self.unique_ids.add(rgb_data.unique_id)


class MSERV3sModuleInfo(AmpioModuleInfo):
    """MSERV-3s Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
            if switch_data and switch_data.unique_id:
                self.configs["switch"].append(switch_data.config)
                self.unique_ids.add(switch_data.unique_id)

        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)


class MROL4sModuleInfo(AmpioModuleInfo):
    """MROL-4s Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            cover_data = AmpioCoverConfig.from_ampio_device(self, item, index)
            if cover_data and cover_data.unique_id:
                self.configs["cover"].append(cover_data.config)
                self.unique_ids.add(cover_data.unique_id)

        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)


class MRT16sModuleInfo(AmpioModuleInfo):
    """MRT-16s Ampio module information (16-channel heating/cooling controller).

    MRT-16s (code 22) is a temperature controller module that supports:
    - 16 independent heating/cooling zones
    - Temperature setpoints via rs/<nr>/cmd
    - Day/Night setpoints via rsdn/<nr>/cmd
    - Operating modes via rm/<nr>/cmd (0=calendar, 1=manual day, 2=manual night, 3=holidays, 4=block)
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create climate entities for temperature zones
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            climate_data = AmpioClimateConfig.from_ampio_device(self, item, index)
            if climate_data and climate_data.unique_id:
                self.configs["climate"].append(climate_data.config)
                self.unique_ids.add(climate_data.unique_id)


class METEO1sModuleInfo(AmpioModuleInfo):
    """METEO-1s Ampio module information (Weather station).

    METEO-1s (code 34) is an outdoor environmental sensor module.
    Provides comprehensive weather data including:
    - Temperature (t/1)
    - Humidity (au16l/1)
    - Wind Speed (au16l/2)
    - Wind Direction (au16/3)
    - Precipitation/Rain (au16l/4)
    - UV Index (au16l/5)
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        sensor_configs: list[AmpioConfig | None] = [
            AmpioTempSensorConfig.from_ampio_device(
                self, ItemName(base64encode("T:Outdoor Temperature")), 1
            ),
        ]

        # Add additional weather sensors based on module capabilities
        if self.au > 0:
            # Humidity sensor
            sensor_configs.append(
                AmpioHumiditySensorConfig.from_ampio_device(
                    self, ItemName(base64encode("HU:Outdoor Humidity")), 1
                )
            )
            # Wind Speed sensor
            sensor_configs.append(
                AmpioWindSpeedSensorConfig.from_ampio_device(
                    self, ItemName(base64encode("Wind Speed")), 1
                )
            )
            # Wind Direction sensor
            sensor_configs.append(
                AmpioWindDirectionSensorConfig.from_ampio_device(
                    self, ItemName(base64encode("Wind Direction")), 1
                )
            )
            # Precipitation/Rain sensor
            sensor_configs.append(
                AmpioPrecipitationSensorConfig.from_ampio_device(
                    self, ItemName(base64encode("Precipitation")), 1
                )
            )
            # UV Index sensor
            sensor_configs.append(
                AmpioUVIndexSensorConfig.from_ampio_device(
                    self, ItemName(base64encode("UV Index")), 1
                )
            )

        for ampio_config in sensor_configs:
            if ampio_config and ampio_config.unique_id:
                self.configs["sensor"].append(ampio_config.config)
                self.unique_ids.add(ampio_config.unique_id)


class MWRCModuleInfo(AmpioModuleInfo):
    """MWRC Ampio module information (Wireless Remote Control).

    MWRC (code 49) is a wireless remote control module.
    Creates binary_sensor entities for remote buttons.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)


class MRDN1sModuleInfo(AmpioModuleInfo):
    """MRDN-1s Ampio module information (Dimmer/RGB driver).

    MRDN-1s (code 38) is a dimmer/RGB driver module.
    Creates light entities with brightness/color support.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


class MRDN5sModuleInfo(AmpioModuleInfo):
    """MRDN-5s: 5-channel dimmer/RGB driver module.

    Extended version of MRDN-1s with 5 dimmable outputs.
    Creates light entities with brightness support.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


# ============================================================================
# INPUT MODULES
# ============================================================================


class MINModuleInfo(AmpioModuleInfo):
    """Base class for M-IN input modules.

    M-IN modules provide binary inputs for switches, sensors, etc.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create binary sensors for all binary inputs
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)


class MIN8sModuleInfo(MINModuleInfo):
    """M-IN-8s: 8 binary inputs (DIN rail)."""


class MIN16sModuleInfo(MINModuleInfo):
    """M-IN-16s: 16 binary inputs (DIN rail)."""


class MIN2pModuleInfo(MINModuleInfo):
    """M-IN-2p: 2 binary inputs (flush-mount)."""


class MIN11pModuleInfo(MINModuleInfo):
    """M-IN-11p: 11 binary inputs (flush-mount)."""


class MINAC4sModuleInfo(MINModuleInfo):
    """M-IN-AC4s: 4 AC voltage inputs."""


class MINAD8sModuleInfo(AmpioModuleInfo):
    """M-IN-AD8s: 8 analog inputs (0-10V or 4-20mA).

    Creates sensor entities for analog values.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create sensors for analog inputs
        for index, item in self.names.get(ItemTypes.AnalogInput, {}).items():
            sensor_data = AmpioAnalogInputSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)


class MINIMP4sModuleInfo(AmpioModuleInfo):
    """M-IN-IMP4s: 4 pulse counter inputs for energy/water meters.

    Creates sensor entities with total_increasing state class.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create sensors for pulse counters
        for index, item in self.names.get(ItemTypes.AnalogOutput32, {}).items():
            sensor_data = AmpioPulseCounterSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)


class MINTCD3pModuleInfo(AmpioModuleInfo):
    """M-IN-TCD3p: 3 NTC temperature sensor inputs."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create temperature sensors
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            sensor_data = AmpioTempSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)


# ============================================================================
# RELAY MODULES
# ============================================================================


class MRELModuleInfo(AmpioModuleInfo):
    """Base class for M-REL relay modules.

    M-REL modules provide relay outputs for switching loads.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create switch entities for relay outputs
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            if item.device_class == "light":
                light_data = AmpioLightConfig.from_ampio_device(self, item, index)
                if light_data and light_data.unique_id:
                    self.configs["light"].append(light_data.config)
                    self.unique_ids.add(light_data.unique_id)
            else:
                switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
                if switch_data and switch_data.unique_id:
                    self.configs["switch"].append(switch_data.config)
                    self.unique_ids.add(switch_data.unique_id)


class MREL2sModuleInfo(MRELModuleInfo):
    """M-REL-2s: 2 relay outputs (DIN rail)."""


class MREL10sModuleInfo(MRELModuleInfo):
    """M-REL-10s: 10 relay outputs (DIN rail)."""


# ============================================================================
# OPEN COLLECTOR OUTPUT MODULES
# ============================================================================


class MOC8sModuleInfo(AmpioModuleInfo):
    """M-OC-8s: 8 open collector outputs (lighting bus)."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


class MOC32sModuleInfo(MOC8sModuleInfo):
    """M-OC-32s: 32 open collector outputs (lighting bus)."""


# ============================================================================
# ANALOG OUTPUT MODULES
# ============================================================================


class MOUT4sModuleInfo(AmpioModuleInfo):
    """MOUT-4s: 4-channel analog output module (DIN rail).

    Provides 0-10V analog outputs for controlling dimmers, valves, etc.
    Creates number entities for analog output control.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Analog outputs as sensors (for monitoring current values)
        for index, item in self.names.get(ItemTypes.AnalogOutput, {}).items():
            sensor_data = AmpioAnalogOutputSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)


class MOUT4pModuleInfo(MOUT4sModuleInfo):
    """MOUT-4p: 4-channel analog output module (flush-mount).

    Same functionality as MOUT-4s but in flush-mount form factor.
    """


# ============================================================================
# INPUT + OUTPUT COMBO MODULES
# ============================================================================


class MINOC4pModuleInfo(AmpioModuleInfo):
    """M-INOC-4p: 4 binary inputs + 4 OC outputs + RGBW controller."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Binary inputs
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)

        # OC outputs as lights
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)

        # Check for RGBW support
        if self.au >= 4:
            rgb_data = AmpioRGBLightConfig.from_ampio_device(self, None, 1)
            if rgb_data and rgb_data.unique_id:
                self.configs["light"].append(rgb_data.config)
                self.unique_ids.add(rgb_data.unique_id)


class MINOC8sModuleInfo(AmpioModuleInfo):
    """M-INOC-8s: 8 binary inputs + 8 OC outputs."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Binary inputs
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)

        # OC outputs
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


# ============================================================================
# ADDITIONAL TOUCH PANELS
# ============================================================================


class MDOT6ModuleInfo(MDOTModuleInfo):
    """MDOT-6 Ampio module information (6-field with display)."""

    _BUTTONS: ClassVar[int] = 6


class MDOT18ModuleInfo(MDOTModuleInfo):
    """MDOT-18 Ampio module information (18-field)."""

    _BUTTONS: ClassVar[int] = 18


# ============================================================================
# ADDITIONAL DIMMER MODULES
# ============================================================================


class MDIM1pModuleInfo(AmpioModuleInfo):
    """M-DIM-1p: 1-channel dimmer (flush-mount)."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


class MDIM2sModuleInfo(MDIM1pModuleInfo):
    """M-DIM-2s: 2-channel dimmer (DIN rail)."""


# ============================================================================
# ADDITIONAL LED MODULES
# ============================================================================


class MLEDsModuleInfo(AmpioModuleInfo):
    """M-LED-s: OWA lighting bus controller (DIN rail)."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.AnalogOutput, {}).items():
            light_data = AmpioDimmableLightConfig.from_ampio_device(self, item, index)
            if light_data and light_data.unique_id:
                self.configs["light"].append(light_data.config)
                self.unique_ids.add(light_data.unique_id)


# ============================================================================
# ADDITIONAL CLIMATE MODULES
# ============================================================================


class MRTsModuleInfo(AmpioModuleInfo):
    """M-RT-s: Temperature controller module.

    Similar to MRT-16s but potentially different number of zones.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Create climate entities for temperature zones
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            climate_data = AmpioClimateConfig.from_ampio_device(self, item, index)
            if climate_data and climate_data.unique_id:
                self.configs["climate"].append(climate_data.config)
                self.unique_ids.add(climate_data.unique_id)


# ============================================================================
# SENSOR MODULES
# ============================================================================


class MSENSLITEModuleInfo(AmpioModuleInfo):
    """M-SENS-LITE: Simplified environmental sensor.

    Provides temperature and humidity (subset of full M-SENS).
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        sensor_configs: list[AmpioConfig | None] = [
            AmpioTempSensorConfig.from_ampio_device(self, ItemName(base64encode("T:Temperature"))),
            AmpioHumiditySensorConfig.from_ampio_device(
                self, ItemName(base64encode("HU:Humidity"))
            ),
        ]

        for ampio_config in sensor_configs:
            if ampio_config and ampio_config.unique_id:
                self.configs["sensor"].append(ampio_config.config)
                self.unique_ids.add(ampio_config.unique_id)


# ============================================================================
# WIRELESS MODULES
# ============================================================================


class WLSensorModuleInfo(AmpioModuleInfo):
    """Base class for wireless sensor modules with battery monitoring."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Add battery level sensor for wireless modules
        # Battery is typically reported in analog channel 1
        battery_data = AmpioBatterySensorConfig.from_ampio_device(
            self, ItemName(base64encode("B:Battery")), 1
        )
        if battery_data and battery_data.unique_id:
            self.configs["sensor"].append(battery_data.config)
            self.unique_ids.add(battery_data.unique_id)


class WZSENSTMPModuleInfo(WLSensorModuleInfo):
    """WZ-SENS-TMP-p: Wireless temperature sensor."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Temperature sensor
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            sensor_data = AmpioTempSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)


class WLREL2pModuleInfo(WLSensorModuleInfo):
    """WL-REL-2p: Wireless 2-relay module with battery monitoring."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
            if switch_data and switch_data.unique_id:
                self.configs["switch"].append(switch_data.config)
                self.unique_ids.add(switch_data.unique_id)


class WLRELROL1pModuleInfo(WLSensorModuleInfo):
    """WL-REL-ROL1p: Wireless roller shutter module with battery monitoring."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            cover_data = AmpioCoverConfig.from_ampio_device(self, item, index)
            if cover_data and cover_data.unique_id:
                self.configs["cover"].append(cover_data.config)
                self.unique_ids.add(cover_data.unique_id)


class WLOCRGBW1pModuleInfo(WLSensorModuleInfo):
    """WL-OC-RGBW1p: Wireless RGBW controller with battery monitoring."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        rgb_data = AmpioRGBLightConfig.from_ampio_device(self, None, 1)
        if rgb_data and rgb_data.unique_id:
            self.configs["light"].append(rgb_data.config)
            self.unique_ids.add(rgb_data.unique_id)


# ============================================================================
# ALARM MODULE
# ============================================================================


class MALARM8sModuleInfo(AmpioModuleInfo):
    """M-ALARM-8s: 8-zone alarm control panel.

    Creates alarm_control_panel and zone binary sensors.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Zone sensors
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)

        # TODO: Add alarm_control_panel entity for arm/disarm control


# ============================================================================
# AUDIO MODULES
# ============================================================================


class MAVAMPsModuleInfo(AmpioModuleInfo):
    """MAV-AMP-s: Audio amplifier module.

    Provides audio amplification with volume control, source selection, and mute.
    Creates sensor entities for volume and source monitoring, and switch for mute.

    Typical configuration:
    - Analog outputs (au): Volume level (0-255), Source selection
    - Binary outputs (o): Mute control (on/off)
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        _LOGGER.debug("MAV-AMP-s: %s", self.names)

        # Volume and source control as sensors (analog outputs for monitoring)
        for index, item in self.names.get(ItemTypes.AnalogOutput, {}).items():
            sensor_data = AmpioAudioSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)

        # Mute control as switch (binary output)
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
            if switch_data and switch_data.unique_id:
                self.configs["switch"].append(switch_data.config)
                self.unique_ids.add(switch_data.unique_id)


# ============================================================================
# RUPS - RELAY UNIT POWER SOCKETS (Type 24)
# ============================================================================


class RUPSModuleInfo(AmpioModuleInfo):
    """RUPS Ampio module information - Relay Unit Power Sockets.

    Handles 230V power socket relay units.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()

        # Binary outputs as switches (power sockets)
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            if item.device_class == "light":
                light_data = AmpioLightConfig.from_ampio_device(self, item, index)
                if light_data and light_data.unique_id:
                    self.configs["light"].append(light_data.config)
                    self.unique_ids.add(light_data.unique_id)
            else:
                switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
                if switch_data and switch_data.unique_id:
                    self.configs["switch"].append(switch_data.config)
                    self.unique_ids.add(switch_data.unique_id)

        # Binary inputs as binary sensors
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)


# ============================================================================
# MKIN-MULTI - MULTI-FUNCTION MODULE (Type 69)
# ============================================================================


class MKINMULTIModuleInfo(AmpioModuleInfo):
    """MKIN-MULTI Ampio module information - Multi-function module.

    Handles multi-function modules that may include:
    - Kinetic buttons
    - Chorus audio
    - IAQ sensors
    - Rekuperator control
    """

    def update_configs(self) -> None:
        """Update module specific configuration with auto-detection."""
        super().update_configs()

        # Binary inputs as binary sensors (kinetic buttons, etc.)
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)

        # Binary outputs as switches
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            if item.device_class == "light":
                light_data = AmpioLightConfig.from_ampio_device(self, item, index)
                if light_data and light_data.unique_id:
                    self.configs["light"].append(light_data.config)
                    self.unique_ids.add(light_data.unique_id)
            else:
                switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
                if switch_data and switch_data.unique_id:
                    self.configs["switch"].append(switch_data.config)
                    self.unique_ids.add(switch_data.unique_id)

        # Temperature sensors
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            sensor_data = AmpioTempSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)

        # Analog inputs as sensors (IAQ, etc.)
        for index, item in self.names.get(ItemTypes.AnalogInput, {}).items():
            analog_data = AmpioAnalogInputSensorConfig.from_ampio_device(self, item, index)
            if analog_data and analog_data.unique_id:
                self.configs["sensor"].append(analog_data.config)
                self.unique_ids.add(analog_data.unique_id)


# ============================================================================
# GENERIC FALLBACK
# ============================================================================


class GenericModuleInfo(AmpioModuleInfo):
    """Generic Ampio module information for unknown module types.

    This class provides a fallback for modules not explicitly supported.
    It attempts to auto-detect entities based on item names and types.
    """

    def update_configs(self) -> None:
        """Update module specific configuration with auto-detection."""
        super().update_configs()

        _LOGGER.warning(
            "Unknown module type %d (%s) detected. Using generic handler. "
            "Consider adding explicit support for this module.",
            self.code,
            self.part_number,
        )

        # Auto-detect binary inputs as binary sensors
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)

        # Auto-detect binary outputs as switches
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            if item.device_class == "light":
                light_data = AmpioLightConfig.from_ampio_device(self, item, index)
                if light_data and light_data.unique_id:
                    self.configs["light"].append(light_data.config)
                    self.unique_ids.add(light_data.unique_id)
            else:
                switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
                if switch_data and switch_data.unique_id:
                    self.configs["switch"].append(switch_data.config)
                    self.unique_ids.add(switch_data.unique_id)

        # Auto-detect temperature sensors
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            sensor_data = AmpioTempSensorConfig.from_ampio_device(self, item, index)
            if sensor_data and sensor_data.unique_id:
                self.configs["sensor"].append(sensor_data.config)
                self.unique_ids.add(sensor_data.unique_id)


CLASS_FACTORY: dict[int, type[AmpioModuleInfo]] = {
    # Touch panels
    6: MDOT6ModuleInfo,
    8: MDOT4ModuleInfo,
    11: MDOT9ModuleInfo,
    18: MDOT18ModuleInfo,
    27: MDOT15LCDModuleInfo,
    33: MDOT2ModuleInfo,
    # Sensors
    44: MSENSModuleInfo,
    45: MSENSLITEModuleInfo,
    34: METEO1sModuleInfo,
    # Roller/Cover
    3: MROL4sModuleInfo,
    # Relay modules
    4: MPR8sModuleInfo,
    7: MREL2sModuleInfo,
    9: MREL10sModuleInfo,
    # Dimmer modules
    5: MDIM8sModuleInfo,
    13: MDIM1pModuleInfo,
    14: MDIM2sModuleInfo,
    # Server/Control
    10: MSERV3sModuleInfo,
    # RGB/LED
    12: MRGBu1ModuleInfo,
    17: MLED1ModuleInfo,
    19: MLEDsModuleInfo,
    # Climate/Heating
    22: MRT16sModuleInfo,
    23: MRTsModuleInfo,
    # RUPS - Relay Unit Power Sockets
    24: RUPSModuleInfo,
    # Integration modules
    25: MCONModuleInfo,
    28: MCON232sModuleInfo,
    29: MCON485sModuleInfo,
    30: MCONDLsModuleInfo,
    31: MCONIRModuleInfo,
    32: MCONHVACpModuleInfo,
    # Output modules
    26: MOC4ModuleInfo,
    35: MOC8sModuleInfo,
    36: MOC32sModuleInfo,
    51: MOUT4sModuleInfo,
    52: MOUT4pModuleInfo,
    # Input modules
    37: MIN8sModuleInfo,
    39: MIN16sModuleInfo,
    40: MIN2pModuleInfo,
    41: MIN11pModuleInfo,
    42: MINAD8sModuleInfo,
    43: MINIMP4sModuleInfo,
    46: MINTCD3pModuleInfo,
    47: MINAC4sModuleInfo,
    # Combo input/output modules
    48: MINOC4pModuleInfo,
    50: MINOC8sModuleInfo,
    # Other
    38: MRDN1sModuleInfo,
    49: MWRCModuleInfo,
    53: MALARM8sModuleInfo,
    54: MAVAMPsModuleInfo,
    55: MRDN5sModuleInfo,
    69: MKINMULTIModuleInfo,
    # Wireless
    56: WLREL2pModuleInfo,
    57: WLRELROL1pModuleInfo,
    58: WLOCRGBW1pModuleInfo,
    59: WZSENSTMPModuleInfo,
    # Generic fallback for unknown module types (code -1 is reserved)
    -1: GenericModuleInfo,
}


@dataclass
class AmpioConfig:
    """Generic Ampio Config class."""

    config: dict[str, Any]

    @property
    def unique_id(self) -> str | None:
        """Return unique_id from config."""
        return self.config.get(CONF_UNIQUE_ID)


class AmpioTempSensorConfig(AmpioConfig):
    """Ampio Temperature Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioTempSensorConfig:
        """Create config from ampio device."""
        if not item.name:
            name = f"Temperature {ampio_device.name}"
        else:
            name = item.name
        mac = ampio_device.user_mac
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-t{index}",
            CONF_NAME: f"ampio-{mac}-t{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_UNIT_OF_MEASUREMENT: "°C",
            CONF_DEVICE_CLASS: "temperature",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/t/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioHumiditySensorConfig(AmpioConfig):
    """Ampio Humidity Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioHumiditySensorConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        if ampio_device.pcb < MSENS_PCB_V3:  # MSENS-1
            state_topic = f"ampio/from/{mac}/state/au32/0"
        else:
            state_topic = f"ampio/from/{mac}/state/au16l/1"
        name = f"Humidity {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-h{index}",
            CONF_NAME: f"ampio-{mac}-h{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_UNIT_OF_MEASUREMENT: "%",
            CONF_DEVICE_CLASS: "humidity",
            CONF_STATE_TOPIC: state_topic,
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioPressureSensorConfig(AmpioConfig):
    """Ampio Pressure Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioPressureSensorConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        if ampio_device.pcb < MSENS_PCB_V3:  # MSENS-1
            state_topic = f"ampio/from/{mac}/state/au32/1"
        else:
            state_topic = f"ampio/from/{mac}/state/au16l/6"
        name = f"Pressure {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-ps{index}",
            CONF_NAME: f"ampio-{mac}-ps{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "pressure",
            CONF_STATE_TOPIC: state_topic,
            CONF_UNIT_OF_MEASUREMENT: "hPa",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioNoiseSensorConfig(AmpioConfig):
    """Ampio Noise Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioNoiseSensorConfig | None:
        """Create config from ampio device."""
        if ampio_device.pcb < MSENS_PCB_V3:  # MSENS-1
            return None
        mac = ampio_device.user_mac
        name = f"Noise {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-n{index}",
            CONF_NAME: f"ampio-{mac}-n{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "signal_strength",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/3",
            CONF_UNIT_OF_MEASUREMENT: "dB",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioIlluminanceSensorConfig(AmpioConfig):
    """Ampio Illuminance Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioIlluminanceSensorConfig | None:
        """Create config from ampio device."""
        if ampio_device.pcb < MSENS_PCB_V3:  # MSENS-1
            return None
        mac = ampio_device.user_mac
        name = f"Illuminance {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-i{index}",
            CONF_NAME: f"ampio-{mac}-i{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "illuminance",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/4",
            CONF_UNIT_OF_MEASUREMENT: "lx",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAirqualitySensorConfig(AmpioConfig):
    """Ampio AirQuality Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioAirqualitySensorConfig | None:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        if ampio_device.pcb < MSENS_PCB_V3:  # MSENS-1
            return None
        name = f"Air Quality {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-aq{index}",
            CONF_NAME: f"ampio-{mac}-aq{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/5",
            CONF_DEVICE_CLASS: "aqi",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioCO2SensorConfig(AmpioConfig):
    """Ampio CO2 Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioCO2SensorConfig | None:
        """Create config from ampio device.

        M-SENS-CO2 variant has CO2 sensor at au16l/7.
        Requires PCB version >= MSENS_PCB_V4 (M-SENS-CO2 variant).
        """
        mac = ampio_device.user_mac
        # M-SENS-CO2 requires PCB version 4 or higher
        if ampio_device.pcb < MSENS_PCB_V4:
            return None
        name = f"CO2 {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-co2{index}",
            CONF_NAME: f"ampio-{mac}-co2{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/7",
            CONF_DEVICE_CLASS: "carbon_dioxide",
            CONF_UNIT_OF_MEASUREMENT: "ppm",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioWindSpeedSensorConfig(AmpioConfig):
    """Ampio Wind Speed Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioWindSpeedSensorConfig:
        """Create config from ampio device.

        Wind speed sensor for METEO-1s weather station.
        Uses au16l topic for 16-bit values with 0.1 resolution.
        """
        mac = ampio_device.user_mac
        name = f"Wind Speed {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-ws{index}",
            CONF_NAME: f"ampio-{mac}-ws{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "wind_speed",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/2",
            CONF_UNIT_OF_MEASUREMENT: "m/s",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioWindDirectionSensorConfig(AmpioConfig):
    """Ampio Wind Direction Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioWindDirectionSensorConfig:
        """Create config from ampio device.

        Wind direction sensor for METEO-1s weather station.
        Returns direction in degrees (0-360).
        """
        mac = ampio_device.user_mac
        name = f"Wind Direction {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-wd{index}",
            CONF_NAME: f"ampio-{mac}-wd{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16/3",
            CONF_UNIT_OF_MEASUREMENT: "°",
            CONF_ICON: "mdi:compass-outline",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioPrecipitationSensorConfig(AmpioConfig):
    """Ampio Precipitation/Rain Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioPrecipitationSensorConfig:
        """Create config from ampio device.

        Precipitation/rain sensor for METEO-1s weather station.
        Returns accumulated precipitation in mm.
        """
        mac = ampio_device.user_mac
        name = f"Precipitation {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-rain{index}",
            CONF_NAME: f"ampio-{mac}-rain{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "precipitation",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/4",
            CONF_UNIT_OF_MEASUREMENT: "mm",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioUVIndexSensorConfig(AmpioConfig):
    """Ampio UV Index Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioUVIndexSensorConfig:
        """Create config from ampio device.

        UV index sensor for METEO-1s weather station.
        Returns UV index value (0-11+).
        """
        mac = ampio_device.user_mac
        name = f"UV Index {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-uv{index}",
            CONF_NAME: f"ampio-{mac}-uv{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/5",
            CONF_ICON: "mdi:sun-wireless-outline",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAnalogFlag8SensorConfig(AmpioConfig):
    """Ampio 8-bit Flag (afu8) Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioAnalogFlag8SensorConfig:
        """Create config from ampio device.

        8-bit flag values (0-255) from state/afu8/<nr>.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Flag 8-bit {index} {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-afu8-{index}",
            CONF_NAME: f"ampio-{mac}-afu8-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/afu8/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAnalogFlag16SensorConfig(AmpioConfig):
    """Ampio 16-bit Signed Flag (afi16) Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioAnalogFlag16SensorConfig:
        """Create config from ampio device.

        16-bit signed flag values (-32768 to 32767) from state/afi16/<nr>.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Flag 16-bit {index} {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-afi16-{index}",
            CONF_NAME: f"ampio-{mac}-afi16-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/afi16/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAnalog16SensorConfig(AmpioConfig):
    """Ampio 16-bit Unsigned (au16) Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioAnalog16SensorConfig:
        """Create config from ampio device.

        16-bit unsigned values (0-65536) from state/au16/<nr>.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Analog 16-bit {index} {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-au16-{index}",
            CONF_NAME: f"ampio-{mac}-au16-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAnalogInputSensorConfig(AmpioConfig):
    """Ampio Analog Input (0-10V / 4-20mA) Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioAnalogInputSensorConfig:
        """Create config from ampio device.

        Analog input values (0-255) from state/a/<nr>.
        Can represent 0-10V or 4-20mA depending on hardware configuration.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Analog Input {index} {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-ain-{index}",
            CONF_NAME: f"ampio-{mac}-ain-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/a/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAnalogOutputSensorConfig(AmpioConfig):
    """Ampio Analog Output (0-10V) Entity Configuration.

    Used for MOUT-4s/4p analog output modules to monitor output values.
    """

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioAnalogOutputSensorConfig:
        """Create config from ampio device.

        Analog output values (0-255) from state/au/<nr>.
        Represents 0-10V output voltage.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Analog Output {index} {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-aout-{index}",
            CONF_NAME: f"ampio-{mac}-aout-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au/{index}",
            CONF_ICON: "mdi:sine-wave",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioBatterySensorConfig(AmpioConfig):
    """Ampio Battery Level Entity Configuration.

    Used for wireless modules to monitor battery level.
    """

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioBatterySensorConfig:
        """Create config from ampio device.

        Battery level (0-100%) from state/a/<nr>.
        """
        mac = ampio_device.user_mac
        name = f"Battery {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-battery-{index}",
            CONF_NAME: f"ampio-{mac}-battery-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "battery",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/a/{index}",
            CONF_UNIT_OF_MEASUREMENT: "%",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioPulseCounterSensorConfig(AmpioConfig):
    """Ampio Pulse Counter (energy/water meter) Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioPulseCounterSensorConfig:
        """Create config from ampio device.

        32-bit counter values from state/au32/<nr>.
        Used for energy meters, water meters, gas meters, etc.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Counter {index} {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-cnt-{index}",
            CONF_NAME: f"ampio-{mac}-cnt-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au32/{index}",
            CONF_DEVICE_CLASS: "energy",  # Default, can be overridden based on item name
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAudioSensorConfig(AmpioConfig):
    """Ampio Audio Sensor Entity Configuration.

    Used for MAV-AMP-s audio amplifier module to monitor volume and source.
    """

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioAudioSensorConfig:
        """Create config from ampio device.

        Audio sensor values (0-255) from state/au/<nr>.
        Typically used for volume level (0-100%) or source selection.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Audio {index} {ampio_device.name}"

        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-audio-{index}",
            CONF_NAME: f"ampio-{mac}-audio-{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au/{index}",
            CONF_ICON: "mdi:volume-high",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        return cls(config=config)


class AmpioTouchSensorConfig(AmpioConfig):
    """Ampio Binary Sensor Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioTouchSensorConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac

        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-i{index}",
            CONF_NAME: f"ampio-{mac}-i{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/i/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
            CONF_DEVICE_CLASS: "opening",
        }

        return cls(config=config)


class AmpioBinarySensorExtendedConfig(AmpioConfig):
    """Ampio Binary Sensor Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioBinarySensorExtendedConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-bi{index}",
            CONF_NAME: f"ampio-{mac}-bi{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/bi/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        return cls(config=config)


class AmpioBinarySensorConfig(AmpioConfig):
    """Ampio Binary Sensor Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioBinarySensorConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-i{index}",
            CONF_NAME: f"ampio-{mac}-i{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/i/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        return cls(config=config)


class AmpioDimmableLightConfig(AmpioConfig):
    """Ampio Dimmable Light Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioDimmableLightConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-a{index}",
            CONF_NAME: f"ampio-{mac}-a{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/o/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_BRIGHTNESS_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_BRIGHTNESS_STATE_TOPIC: f"ampio/from/{mac}/state/a/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        if ampio_device.code == ModuleCodes.MLED1:
            config[CONF_ICON] = "mdi:spotlight"

        return cls(config=config)


class AmpioLightConfig(AmpioConfig):
    """Ampio Light Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioLightConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-a{index}",
            CONF_NAME: f"ampio-{mac}-a{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/o/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        return cls(config=config)


class AmpioRGBLightConfig(AmpioConfig):
    """Ampio RGB Light Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName | None = None, index: int = 1
    ) -> AmpioRGBLightConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        name = ampio_device.name or "RGBW"
        index = 1
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-rgbw{index}",
            CONF_NAME: f"ampio-{mac}-rgbw{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_RGB_STATE_TOPIC: f"ampio/from/{mac}/state/rgbw/{index}",
            CONF_RGB_COMMAND_TOPIC: f"ampio/to/{mac}/rgbw/{index}/cmd",
            CONF_WHITE_VALUE_STATE_TOPIC: f"ampio/from/{mac}/state/a/4",
            CONF_WHITE_VALUE_COMMAND_TOPIC: f"ampio/to/{mac}/o/4/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        return cls(config=config)


class AmpioSwitchConfig(AmpioConfig):
    """Ampio Switch Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioSwitchConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-bo{index}",
            CONF_NAME: f"ampio-{mac}-bo{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/o/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        if device_class == "heat":
            config[CONF_ICON] = "mdi:radiator"

        return cls(config=config)


class AmpioFlagConfig(AmpioConfig):
    """Ampio Flag Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioFlagConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-f{index}",
            CONF_NAME: f"ampio-{mac}-f{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/f/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/f/{index}/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        config[CONF_ICON] = "mdi:flag"

        return cls(config=config)


class AmpioCoverConfig(AmpioConfig):
    """Ampio Cover Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioCoverConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        icon = None
        device_class = item.device_class
        if device_class is None:
            device_class = "shutter"
        if device_class == "valve":
            icon = "mdi:valve"

        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-co{index}",
            CONF_NAME: f"ampio-{mac}-co{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/a/{index}",
            CONF_CLOSING_STATE_TOPIC: f"ampio/from/{mac}/state/o/{2 * (index - 1) + 1}",
            CONF_OPENING_STATE_TOPIC: f"ampio/from/{mac}/state/o/{2 * (index)}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_RAW_TOPIC: f"ampio/to/{mac}/raw",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class not in ["garage", "valve"]:
            config.update(
                {
                    CONF_TILT_POSITION_TOPIC: f"ampio/from/{mac}/state/a/{6 + index}",
                }
            )

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        if icon:
            config[CONF_ICON] = icon

        return cls(config=config)


class AmpioSatelConfig(AmpioConfig):
    """Ampio Satel single Entity configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo) -> AmpioSatelConfig:
        """Create alarm config from ampio device."""
        away: set[int] = set()
        home: set[int] = set()
        items: dict[int, ItemName] = ampio_device.names.get(ItemTypes.AnalogOutput, {})
        mac = ampio_device.user_mac
        for index, item in items.items():
            if item.prefix in ("A", "B", None):  # Away or Both or Not defined
                away.add(index)
            if item.prefix in ("H", "B"):  # Home or Both
                home.add(index)

        mac = ampio_device.user_mac
        prefix = f"ampio/from/{mac}/state"
        config = {
            CONF_AWAY_ZONES: away,
            CONF_HOME_ZONES: home,
            CONF_UNIQUE_ID: f"ampio-{mac}-alarm",
            CONF_NAME: f"ampio-{mac}-alarm",
            CONF_FRIENDLY_NAME: ampio_device.name,
            CONF_RAW_TOPIC: f"ampio/to/{mac}/raw",
            CONF_ARMED_TOPIC: f"{prefix}/armed/+",
            CONF_ALARM_TOPIC: f"{prefix}/alarm/+",
            CONF_ENTRYTIME_TOPIC: f"{prefix}/entrytime/+",
            CONF_EXITTIME10_TOPIC: f"{prefix}/exittime10/+",
            CONF_EXITTIME_TOPIC: f"{prefix}/exittime/+",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        return cls(config=config)


class AmpioClimateConfig(AmpioConfig):
    """Ampio Climate Entity Configuration.

    Supports MRT-16s temperature controllers with:
    - Temperature reading: state/t/<nr>
    - Setpoint control: rs/<nr>/cmd (-99.9 to 155.0)
    - Mode control: rm/<nr>/cmd (0=calendar, 1=manual day, 2=manual night, 3=holidays, 4=block)
    """

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioClimateConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Climate Zone {index} {ampio_device.name}"

        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-climate{index}",
            CONF_NAME: f"ampio-{mac}-climate{index}",
            CONF_FRIENDLY_NAME: name,
            # Temperature reading
            CONF_TEMPERATURE_STATE_TOPIC: f"ampio/from/{mac}/state/t/{index}",
            # Setpoint control
            CONF_SETPOINT_STATE_TOPIC: f"ampio/from/{mac}/state/rs/{index}",
            CONF_SETPOINT_COMMAND_TOPIC: f"ampio/to/{mac}/rs/{index}/cmd",
            # Mode control
            CONF_MODE_STATE_TOPIC: f"ampio/from/{mac}/state/rm/{index}",
            CONF_MODE_COMMAND_TOPIC: f"ampio/to/{mac}/rm/{index}/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        return cls(config=config)


class AmpioEventConfig(AmpioConfig):
    """Ampio Event Entity Configuration.

    Used for button press events on touch panels, RFID scans, and gesture detection.
    """

    @classmethod
    def from_ampio_device(
        cls, ampio_device: AmpioModuleInfo, item: ItemName, index: int = 1
    ) -> AmpioEventConfig:
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Button {index} {ampio_device.name}"

        config: dict[str, Any] = {
            CONF_UNIQUE_ID: f"ampio-{mac}-event{index}",
            CONF_NAME: f"ampio-{mac}-event{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/i/{index}",
            CONF_DEVICE_CLASS: "button",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        return cls(config=config)
