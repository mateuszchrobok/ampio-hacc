# Platform Development Guide

This guide explains how to add support for new Ampio module types or create new Home Assistant platforms.

## Overview

The Ampio integration uses a modular architecture:

1. **Module Info Classes** (`models.py`) - Parse discovery data and generate entity configs
2. **Entity Config Classes** (`models.py`) - Define entity configuration dictionaries
3. **Platform Files** (`sensor.py`, `light.py`, etc.) - Create Home Assistant entities
4. **Base Entity Class** (`entity.py`) - Common entity functionality

## Adding a New Module Type

### Step 1: Identify the Module

First, identify the module's type code. When the integration encounters an unknown module, it logs:

```
Unknown module type 99 (99) detected. Using generic handler.
```

The number is the type code you'll use.

### Step 2: Create Module Info Class

In `models.py`, create a class that inherits from `AmpioModuleInfo`:

```python
class MyModuleInfo(AmpioModuleInfo):
    """My new module information.

    MYM-8s (code 99) is an 8-channel widget controller.
    """

    def update_configs(self) -> None:
        """Update module specific configuration."""
        # Always call parent first
        super().update_configs()

        # Create entities for binary outputs
        for index, item in self.names.get(ItemTypes.BinaryOutput, {}).items():
            switch_data = AmpioSwitchConfig.from_ampio_device(self, item, index)
            if switch_data and switch_data.unique_id:
                self.configs["switch"].append(switch_data.config)
                self.unique_ids.add(switch_data.unique_id)

        # Create entities for binary inputs
        for index, item in self.names.get(ItemTypes.BinaryInput, {}).items():
            binary_data = AmpioBinarySensorConfig.from_ampio_device(self, item, index)
            if binary_data and binary_data.unique_id:
                self.configs["binary_sensor"].append(binary_data.config)
                self.unique_ids.add(binary_data.unique_id)
```

### Step 3: Register in CLASS_FACTORY

Add your class to the `CLASS_FACTORY` dictionary:

```python
CLASS_FACTORY: dict[int, type[AmpioModuleInfo]] = {
    # ... existing entries ...
    99: MyModuleInfo,  # Add your module
}
```

### Step 4: Test Discovery

1. Restart Home Assistant
2. Reload the integration
3. Check logs for your module being discovered
4. Verify entities are created

## Creating Entity Config Classes

If existing config classes don't fit your needs, create a new one:

```python
class AmpioWidgetSensorConfig(AmpioConfig):
    """Ampio Widget Sensor Entity Configuration."""

    @classmethod
    def from_ampio_device(
        cls,
        ampio_device: AmpioModuleInfo,
        item: ItemName,
        index: int = 1
    ) -> AmpioWidgetSensorConfig:
        """Create config from ampio device.

        Args:
            ampio_device: The parent module info.
            item: The item name data.
            index: Item index (1-based).

        Returns:
            Config instance with populated configuration dict.
        """
        mac = ampio_device.user_mac
        name = item.name if item.name else f"Widget {index} {ampio_device.name}"

        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-widget{index}",
            CONF_NAME: f"ampio-{mac}-widget{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/widget/{index}",
            CONF_DEVICE_CLASS: "widget",
            CONF_UNIT_OF_MEASUREMENT: "widgets",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        return cls(config=config)
```

## Adding a New Platform

### Step 1: Create Platform File

Create `custom_components/ampio/new_platform.py`:

```python
"""Support for Ampio new platform entities."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.new_platform import NewPlatformEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_COMMAND_TOPIC,
    CONF_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_COORDINATOR,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio new platform entities."""

    @callback
    def async_add_new_platform_entities() -> None:
        """Add new platform entities from discovery."""
        coordinator = hass.data[DATA_AMPIO].get(DATA_AMPIO_COORDINATOR)
        if not coordinator:
            return

        configs = coordinator.get_entity_configs("new_platform")
        entities = [
            AmpioNewPlatformEntity(config)
            for config in configs
        ]

        if entities:
            async_add_entities(entities)
            _LOGGER.info("Added %d new platform entities", len(entities))

    # Register for discovery signal
    async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        async_add_new_platform_entities,
    )

    # Add any already discovered entities
    async_add_new_platform_entities()


class AmpioNewPlatformEntity(AmpioEntity, NewPlatformEntity):
    """Ampio new platform entity."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the entity."""
        super().__init__(config)
        self._state_topic = config.get(CONF_STATE_TOPIC)
        self._command_topic = config.get(CONF_COMMAND_TOPIC)

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""
        if not self._state_topic:
            return

        if self.coordinator and self.coordinator.mqtt_client:
            await self.coordinator.mqtt_client.async_subscribe(
                self._state_topic,
                DEFAULT_QOS
            )

    @callback
    def _handle_state_message(self, msg: Any) -> None:
        """Handle incoming state message."""
        try:
            self._state = msg.payload
            self._available = True
            self.async_write_ha_state()
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Error parsing state: %s", err)

    @property
    def state(self) -> Any:
        """Return the state."""
        return self._state

    async def async_do_something(self, **kwargs: Any) -> None:
        """Handle a service call."""
        if self._command_topic:
            self.publish(self._command_topic, "command_value")
```

### Step 2: Register the Platform

Add to `COMPONENTS` in `const.py`:

```python
from homeassistant.components.new_platform import DOMAIN as NEW_PLATFORM

COMPONENTS: Final = (
    ALARM_CONTROL_PANEL,
    BINARY_SENSOR,
    # ... existing platforms ...
    NEW_PLATFORM,  # Add new platform
)
```

### Step 3: Update Module Info

Ensure module info classes populate configs for your new platform:

```python
def update_configs(self) -> None:
    super().update_configs()

    # Add entities for new platform
    for index, item in self.names.get(ItemTypes.SomeType, {}).items():
        config = AmpioNewPlatformConfig.from_ampio_device(self, item, index)
        if config and config.unique_id:
            self.configs["new_platform"].append(config.config)
            self.unique_ids.add(config.unique_id)
```

## MQTT Message Handling

### State Updates

Entities receive state updates through MQTT subscriptions:

```python
async def subscribe_topics(self) -> None:
    """Subscribe to state topics."""
    if self._state_topic and self.coordinator and self.coordinator.mqtt_client:
        await self.coordinator.mqtt_client.async_subscribe(
            self._state_topic,
            DEFAULT_QOS
        )
```

The coordinator routes messages to entities. Handle state in your entity:

```python
@callback
def _handle_state_message(self, msg: Message) -> None:
    """Handle state update."""
    self._state = msg.payload
    self.async_write_ha_state()
```

### Commands

Send commands using the coordinator:

```python
async def async_turn_on(self, **kwargs: Any) -> None:
    """Turn on the device."""
    self.publish(self._command_topic, "1")
```

## Item Types

Available item types in `ItemTypes` enum:

| Type | Code | Description |
|------|------|-------------|
| `Temperature` | `t` | Temperature sensor |
| `BinaryFlag` | `f` | Boolean flag |
| `BinaryInput` | `i` | Binary input |
| `BinaryOutput` | `o` | Binary output |
| `AnalogInput` | `a` | Analog input (0-255) |
| `AnalogOutput` | `au` | Analog output (0-255) |
| `AnalogOutput16` | `au16` | 16-bit unsigned |
| `AnalogOutput16L` | `au16l` | 16-bit / 10 |
| `AnalogOutput32` | `au32` | 32-bit unsigned |
| `RGB` | `rgb` | RGB color |
| `RGBW` | `rgbw` | RGBW color |
| `Setpoint` | `rs` | Temperature setpoint |
| `Mode` | `rm` | Operating mode |

## Testing Your Changes

### Unit Tests

Create tests in `tests/test_new_platform.py`:

```python
"""Tests for Ampio new platform."""

import pytest
from unittest.mock import MagicMock, patch

from custom_components.ampio.new_platform import AmpioNewPlatformEntity


def test_entity_creation():
    """Test entity is created with correct config."""
    config = {
        "unique_id": "ampio-AABB-widget1",
        "name": "ampio-AABB-widget1",
        "friendly_name": "Test Widget",
        "state_topic": "ampio/from/AABB/state/widget/1",
    }

    entity = AmpioNewPlatformEntity(config)

    assert entity.unique_id == "ampio-AABB-widget1"
    assert entity.name == "Test Widget"
```

### Integration Tests

Test with a real Ampio system:

1. Enable debug logging
2. Watch for discovery messages
3. Verify entity states update
4. Test commands work

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_new_platform.py -v

# Run with coverage
pytest tests/ -v --cov=custom_components.ampio
```

## Best Practices

### Entity Naming

- Use consistent unique_id format: `ampio-{mac}-{type}{index}`
- Derive friendly_name from item name
- Support device class prefixes in item names

### Error Handling

```python
@callback
def _handle_state_message(self, msg: Message) -> None:
    """Handle state with proper error handling."""
    try:
        value = float(msg.payload)
        self._state = value
        self._available = True
    except (ValueError, TypeError) as err:
        _LOGGER.warning(
            "Invalid payload for %s: %s (%s)",
            self.entity_id,
            msg.payload,
            err
        )
        # Don't update state on error
    finally:
        self.async_write_ha_state()
```

### Logging

```python
_LOGGER = logging.getLogger(__name__)

# Use appropriate log levels
_LOGGER.debug("State update: %s", value)  # Verbose
_LOGGER.info("Entity added: %s", entity_id)  # Normal operations
_LOGGER.warning("Invalid data: %s", data)  # Recoverable issues
_LOGGER.error("Failed to connect: %s", err)  # Errors
```

### Code Style

- Follow Home Assistant coding standards
- Use type hints
- Add docstrings to classes and methods
- Run ruff/mypy before committing

```bash
# Lint
ruff check custom_components/ampio

# Type check
mypy custom_components/ampio

# Format
ruff format custom_components/ampio
```
