"""Ampio Binary Sensor platform."""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_CLASS, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import discovery, subscription
from .const import (
    CONF_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AmpioBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an Ampio binary sensor entity."""

    # No additional fields needed - we use the standard BinarySensorEntityDescription fields


# Map device class strings to BinarySensorEntityDescription
BINARY_SENSOR_DESCRIPTIONS: dict[str, AmpioBinarySensorEntityDescription] = {
    "door": AmpioBinarySensorEntityDescription(
        key="door",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    "window": AmpioBinarySensorEntityDescription(
        key="window",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    "motion": AmpioBinarySensorEntityDescription(
        key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    "opening": AmpioBinarySensorEntityDescription(
        key="opening",
        device_class=BinarySensorDeviceClass.OPENING,
    ),
    "occupancy": AmpioBinarySensorEntityDescription(
        key="occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    ),
    "presence": AmpioBinarySensorEntityDescription(
        key="presence",
        device_class=BinarySensorDeviceClass.PRESENCE,
    ),
    "smoke": AmpioBinarySensorEntityDescription(
        key="smoke",
        device_class=BinarySensorDeviceClass.SMOKE,
    ),
    "gas": AmpioBinarySensorEntityDescription(
        key="gas",
        device_class=BinarySensorDeviceClass.GAS,
    ),
    "moisture": AmpioBinarySensorEntityDescription(
        key="moisture",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    "light": AmpioBinarySensorEntityDescription(
        key="light",
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    "power": AmpioBinarySensorEntityDescription(
        key="power",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    "problem": AmpioBinarySensorEntityDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    "safety": AmpioBinarySensorEntityDescription(
        key="safety",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
    "sound": AmpioBinarySensorEntityDescription(
        key="sound",
        device_class=BinarySensorDeviceClass.SOUND,
    ),
    "vibration": AmpioBinarySensorEntityDescription(
        key="vibration",
        device_class=BinarySensorDeviceClass.VIBRATION,
    ),
    "battery": AmpioBinarySensorEntityDescription(
        key="battery",
        device_class=BinarySensorDeviceClass.BATTERY,
    ),
    "cold": AmpioBinarySensorEntityDescription(
        key="cold",
        device_class=BinarySensorDeviceClass.COLD,
    ),
    "connectivity": AmpioBinarySensorEntityDescription(
        key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    "heat": AmpioBinarySensorEntityDescription(
        key="heat",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    "lock": AmpioBinarySensorEntityDescription(
        key="lock",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    "moving": AmpioBinarySensorEntityDescription(
        key="moving",
        device_class=BinarySensorDeviceClass.MOVING,
    ),
    "plug": AmpioBinarySensorEntityDescription(
        key="plug",
        device_class=BinarySensorDeviceClass.PLUG,
    ),
}

# Default description for sensors without a specific device class
DEFAULT_BINARY_SENSOR_DESCRIPTION = AmpioBinarySensorEntityDescription(
    key="generic",
)


class AmpioBinarySensor(AmpioEntity, RestoreEntity, BinarySensorEntity):
    """Representation of an Ampio Binary Sensor."""

    entity_description: AmpioBinarySensorEntityDescription

    def __init__(
        self,
        config: dict[str, Any],
        description: AmpioBinarySensorEntityDescription | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(config)

        # Get or create entity description
        device_class_str = config.get(CONF_DEVICE_CLASS)
        if description:
            self.entity_description = description
        elif device_class_str and device_class_str in BINARY_SENSOR_DESCRIPTIONS:
            self.entity_description = BINARY_SENSOR_DESCRIPTIONS[device_class_str]
        else:
            self.entity_description = DEFAULT_BINARY_SENSOR_DESCRIPTION

        # Set device class from description
        self._attr_device_class = self.entity_description.device_class

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._state

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""

        @callback
        def state_message_received(msg: Any) -> None:
            """Handle new MQTT message."""
            self._state = self.parse_bool_state(msg.payload, self.name or "binary_sensor")
            self.async_write_ha_state()

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass,
            self._sub_state,
            self._create_topic_config(CONF_STATE_TOPIC, state_message_received),
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = last_state.state == STATE_ON

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio binary sensors from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][BINARY_SENSOR_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioBinarySensor,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
