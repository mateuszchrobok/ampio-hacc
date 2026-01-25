# API Reference

This document provides detailed API documentation for developers working with or extending the Ampio integration.

## Core Classes

### AmpioCoordinator

Central orchestrator for the integration. Manages MQTT connection, device discovery, and entity coordination.

```python
class AmpioCoordinator(DataUpdateCoordinator[AmpioData]):
    """Coordinator for Ampio MQTT data.

    The coordinator handles:
    - MQTT connection lifecycle
    - Device discovery and registration
    - Entity configuration collection
    - Message routing to entities

    Attributes:
        config_entry: The ConfigEntry for this integration instance.
        data: AmpioData containing modules and entity configs.
    """
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `mqtt_client` | `AmpioMQTTClient \| None` | The underlying MQTT client |
| `data` | `AmpioData` | Current integration data |

#### Methods

##### async_setup

```python
async def async_setup(self) -> None:
    """Set up the coordinator.

    Connects to MQTT broker and starts device discovery.

    Raises:
        ConfigEntryNotReady: If connection fails.

    Example:
        coordinator = AmpioCoordinator(hass, config_entry)
        await coordinator.async_setup()
    """
```

##### async_shutdown

```python
async def async_shutdown(self) -> None:
    """Shut down the coordinator.

    Disconnects from MQTT broker and cleans up resources.
    """
```

##### async_publish

```python
async def async_publish(
    self,
    topic: str,
    payload: PublishPayloadType,
    qos: int = 0,
    retain: bool = False
) -> None:
    """Publish an MQTT message.

    Args:
        topic: MQTT topic to publish to.
        payload: Message payload (str, bytes, int, float, or None).
        qos: Quality of service level (0, 1, or 2).
        retain: Whether to retain the message.

    Example:
        await coordinator.async_publish(
            "ampio/to/AABB/o/1/cmd",
            "1",
            qos=0,
            retain=False
        )
    """
```

##### publish

```python
def publish(
    self,
    topic: str,
    payload: PublishPayloadType,
    qos: int = 0,
    retain: bool = False
) -> None:
    """Publish an MQTT message (non-async wrapper).

    Schedules the publish as a task. Use from synchronous code.

    Args:
        topic: MQTT topic to publish to.
        payload: Message payload.
        qos: Quality of service level.
        retain: Whether to retain the message.
    """
```

##### get_entity_configs

```python
def get_entity_configs(self, component: str) -> list[dict[str, Any]]:
    """Get entity configurations for a component.

    Args:
        component: Platform name (e.g., "sensor", "light").

    Returns:
        List of entity configuration dictionaries.

    Example:
        sensor_configs = coordinator.get_entity_configs("sensor")
        for config in sensor_configs:
            print(config["unique_id"])
    """
```

---

### AmpioData

Data container for the integration.

```python
@dataclass
class AmpioData:
    """Class to hold Ampio integration data.

    Attributes:
        modules: Dict mapping MAC addresses to AmpioModuleInfo.
        unique_ids: Set of created entity unique IDs (prevents duplicates).
        entity_configs: Dict mapping platform names to config lists.
        server_version: Ampio MQTT Bridge version string.
    """

    modules: dict[str, AmpioModuleInfo] = field(default_factory=dict)
    unique_ids: set[str] = field(default_factory=set)
    entity_configs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    server_version: str | None = None
```

---

### AmpioMQTTClient

Low-level MQTT client wrapper with async support.

```python
class AmpioMQTTClient:
    """Ampio MQTT Client wrapper.

    Provides async interface to paho-mqtt client with Home Assistant
    integration patterns.

    Attributes:
        hass: Home Assistant instance.
        config_entry: Configuration entry.
        connected: Boolean indicating connection state.
    """
```

#### Methods

##### async_connect

```python
async def async_connect(self) -> str:
    """Connect to the MQTT broker.

    Returns:
        "OK" on success, error message on failure.

    Example:
        result = await client.async_connect()
        if result != "OK":
            raise ConfigEntryNotReady(result)
    """
```

##### async_disconnect

```python
async def async_disconnect(self) -> None:
    """Disconnect from the MQTT broker."""
```

##### async_subscribe

```python
async def async_subscribe(self, topic: str, qos: int = 0) -> None:
    """Subscribe to an MQTT topic.

    Args:
        topic: Topic pattern (supports + and # wildcards).
        qos: Quality of service level.

    Example:
        await client.async_subscribe("ampio/from/+/state/#", qos=0)
    """
```

##### async_publish

```python
async def async_publish(
    self,
    topic: str,
    payload: PublishPayloadType,
    qos: int,
    retain: bool
) -> None:
    """Publish an MQTT message.

    Args:
        topic: Destination topic.
        payload: Message payload.
        qos: Quality of service.
        retain: Retain flag.
    """
```

---

## Model Classes

### AmpioModuleInfo

Base class representing an Ampio hardware module.

```python
@dataclass
class AmpioModuleInfo:
    """Ampio Module Information.

    Base class for all module types. Subclasses implement
    update_configs() to generate platform-specific entities.

    Attributes:
        mac: Hardware MAC address (CAN bus).
        user_mac: User-assigned MAC (used in MQTT topics).
        code: Module type code (see TYPE_CODES).
        pcb: PCB version number.
        software: Firmware version.
        protocol: Protocol version.
        date_prod: Production date (YYYYMMDD).
        i: Number of binary inputs.
        o: Number of binary outputs.
        a: Number of analog inputs.
        au: Number of analog outputs.
        t: Number of temperature sensors.
        flags: Number of flags.
        name: Module display name (decoded from base64).
        names: Dict of item names by type and index.
        configs: Dict of entity configs by platform.
        unique_ids: Set of entity unique IDs for this module.
    """
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `part_number` | `str \| int` | Human-readable module code (e.g., "M-SENS") |
| `model` | `str` | Full model string with MAC addresses |

#### Methods

##### update_configs

```python
def update_configs(self) -> None:
    """Update the config data for entities.

    Called after item names are received. Populates self.configs
    with entity configurations for each supported platform.

    Override in subclasses to implement module-specific entity creation.

    Example implementation:
        def update_configs(self) -> None:
            super().update_configs()
            for index, item in self.names.get(ItemTypes.Temperature, {}).items():
                config = AmpioTempSensorConfig.from_ampio_device(self, item, index)
                if config and config.unique_id:
                    self.configs["sensor"].append(config.config)
                    self.unique_ids.add(config.unique_id)
    """
```

##### as_hass_device

```python
def as_hass_device(self) -> dict[str, Any]:
    """Return info in Home Assistant device format.

    Returns:
        Dict suitable for DeviceInfo(**result).

    Example:
        device_info = module.as_hass_device()
        # {
        #     "connections": {("mac", "AABB")},
        #     "identifiers": {("ampio", "AABB")},
        #     "name": "Kitchen Sensor",
        #     "manufacturer": "Ampio",
        #     "model": "M-SENS [1B88/AABB]",
        #     "sw_version": 341,
        #     "via_device": ("ampio", "ampio-mqtt"),
        # }
    """
```

##### from_topic_payload (classmethod)

```python
@classmethod
def from_topic_payload(cls, payload: dict[str, Any]) -> list[AmpioModuleInfo]:
    """Create module objects from discovery payload.

    Factory method that creates appropriate subclass instances
    based on module type code.

    Args:
        payload: JSON payload from ampio/from/can/dev/list.

    Returns:
        List of AmpioModuleInfo (or subclass) instances.
    """
```

##### get_config_for_component

```python
def get_config_for_component(self, component: str) -> list[Any]:
    """Return list of entity configs for specific component.

    Args:
        component: Platform name.

    Returns:
        List of configuration dicts.
    """
```

---

### ItemName

Parsed item name with device class extraction.

```python
@dataclass
class ItemName:
    """Name of an Ampio module item.

    Parses base64-encoded names and extracts device class from prefix.

    Attributes:
        d: Raw data (decoded from base64 after init).
        name: Display name (after prefix removal).
        device_class: Extracted device class or None.
        prefix: Original prefix or None.

    Example:
        item = ItemName("VDpLaXRjaGVu")  # "T:Kitchen" in base64
        assert item.name == "Kitchen"
        assert item.device_class == "temperature"
        assert item.prefix == "T"
    """
```

---

### Message

MQTT message container.

```python
@dataclass(frozen=True, slots=True)
class Message:
    """MQTT Message.

    Immutable container for received MQTT messages.

    Attributes:
        topic: Message topic.
        payload: Message payload (str, bytes, int, float, or None).
        qos: Quality of service level.
        retain: Whether message was retained.
        subscribed_topic: The subscription pattern that matched.
        timestamp: UTC timestamp when received.
    """
```

---

## Entity Classes

### AmpioEntity

Base class for all Ampio entities.

```python
class AmpioEntity(StateMessageMixin, Entity):
    """Base class for Ampio entities.

    Provides common functionality:
    - Device info integration
    - MQTT topic subscription
    - State management
    - Coordinator access

    Attributes:
        _attr_has_entity_name: True (uses device name + entity name).
        _attr_should_poll: False (push-based updates).
    """
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `coordinator` | `AmpioCoordinator \| None` | Access to coordinator |
| `name` | `str \| None` | Entity name suffix |
| `available` | `bool` | Entity availability |
| `extra_state_attributes` | `dict \| None` | Additional attributes |

#### Methods

##### subscribe_topics

```python
async def subscribe_topics(self) -> None:
    """Subscribe to MQTT topics for this entity.

    Override in subclasses to set up topic subscriptions.
    Called from async_added_to_hass().

    Example:
        async def subscribe_topics(self) -> None:
            topic = self._config.get(CONF_STATE_TOPIC)
            if topic and self.coordinator and self.coordinator.mqtt_client:
                await self.coordinator.mqtt_client.async_subscribe(topic)
    """
```

##### publish

```python
def publish(
    self,
    topic: str,
    payload: str | bytes | int | float,
    qos: int = 0,
    retain: bool = False
) -> None:
    """Publish an MQTT message.

    Convenience method using the coordinator's publish function.

    Args:
        topic: Destination topic.
        payload: Message payload.
        qos: Quality of service.
        retain: Retain flag.
    """
```

---

## Configuration Classes

### AmpioConfig

Base class for entity configuration.

```python
@dataclass
class AmpioConfig:
    """Generic Ampio Config class.

    Attributes:
        config: Dictionary of entity configuration.

    Properties:
        unique_id: Returns the unique_id from config.
    """
```

### Sensor Configs

| Class | Description | Key Topics |
|-------|-------------|------------|
| `AmpioTempSensorConfig` | Temperature sensor | `state/t/{n}` |
| `AmpioHumiditySensorConfig` | Humidity sensor | `state/au16l/1` |
| `AmpioPressureSensorConfig` | Pressure sensor | `state/au16l/6` |
| `AmpioNoiseSensorConfig` | Noise level | `state/au16l/3` |
| `AmpioIlluminanceSensorConfig` | Light level | `state/au16l/4` |
| `AmpioAirqualitySensorConfig` | Air quality index | `state/au16l/5` |
| `AmpioCO2SensorConfig` | CO2 level | `state/au16l/7` |

### Other Configs

| Class | Description |
|-------|-------------|
| `AmpioSwitchConfig` | Binary output switch |
| `AmpioLightConfig` | On/off light |
| `AmpioDimmableLightConfig` | Dimmable light |
| `AmpioRGBLightConfig` | RGB/RGBW light |
| `AmpioCoverConfig` | Cover/shutter |
| `AmpioClimateConfig` | Climate zone |
| `AmpioBinarySensorConfig` | Binary input sensor |
| `AmpioTouchSensorConfig` | Touch panel button |
| `AmpioEventConfig` | Button event |
| `AmpioSatelConfig` | Satel alarm panel |
| `AmpioFlagConfig` | System flag |

---

## Constants

### Data Storage Keys

```python
DATA_AMPIO = "ampio"
DATA_AMPIO_COORDINATOR = "coordinator"
DATA_AMPIO_MODULES = "modules"
DATA_AMPIO_UNIQUE_IDS = "unique_ids"
```

### Signals

```python
SIGNAL_ADD_ENTITIES = "ampio_add_new_entities"
AMPIO_CONNECTED = "ampio_connected"
AMPIO_DISCONNECTED = "ampio_disconnected"
```

### Module Type Codes

See `TYPE_CODES` in `models.py` for complete mapping:

```python
TYPE_CODES = {
    3: "MROL-4s",
    4: "MPR-8s",
    5: "MDIM-8s",
    # ... see models.py for full list
    44: "MSENS",
    45: "MSENS-LITE",
}
```

---

## Usage Examples

### Access Coordinator from Entity

```python
class MyAmpioEntity(AmpioEntity):
    async def async_turn_on(self, **kwargs):
        if self.coordinator:
            await self.coordinator.async_publish(
                self._command_topic,
                "1",
                qos=0,
                retain=False
            )
```

### Create Custom Module Handler

```python
class MyModuleInfo(AmpioModuleInfo):
    """Handler for custom module type."""

    def update_configs(self) -> None:
        super().update_configs()

        # Create sensors for temperature items
        for index, item in self.names.get(ItemTypes.Temperature, {}).items():
            config = AmpioTempSensorConfig.from_ampio_device(self, item, index)
            if config and config.unique_id:
                self.configs["sensor"].append(config.config)
                self.unique_ids.add(config.unique_id)

# Register in CLASS_FACTORY
CLASS_FACTORY[99] = MyModuleInfo
```

### Subscribe to Entity State Updates

```python
async def subscribe_topics(self) -> None:
    """Subscribe to state topic."""
    topic_config = self._create_topic_config(
        CONF_STATE_TOPIC,
        self._handle_state_message,
        DEFAULT_QOS,
    )
    if topic_config and self.coordinator and self.coordinator.mqtt_client:
        for key, config in topic_config.items():
            await self.coordinator.mqtt_client.async_subscribe(
                config["topic"],
                config["qos"]
            )
```
