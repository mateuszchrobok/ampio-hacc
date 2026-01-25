"""Ampio Switch platform."""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
)
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import discovery, subscription
from .const import (
    CONF_COMMAND_TOPIC,
    CONF_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    SIGNAL_ADD_ENTITIES,
    SWITCH_CMD_OFF,
    SWITCH_CMD_ON,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AmpioSwitchEntityDescription(SwitchEntityDescription):
    """Describes an Ampio switch entity."""

    # No additional fields needed - we use the standard SwitchEntityDescription fields


# Map device class strings to SwitchEntityDescription
SWITCH_DESCRIPTIONS: dict[str, AmpioSwitchEntityDescription] = {
    "outlet": AmpioSwitchEntityDescription(
        key="outlet",
        device_class=SwitchDeviceClass.OUTLET,
    ),
    "switch": AmpioSwitchEntityDescription(
        key="switch",
        device_class=SwitchDeviceClass.SWITCH,
    ),
}

# Default description for switches without a specific device class
DEFAULT_SWITCH_DESCRIPTION = AmpioSwitchEntityDescription(
    key="generic",
    device_class=SwitchDeviceClass.SWITCH,
)


class AmpioSwitch(AmpioEntity, SwitchEntity):
    """Representation of an Ampio Switch."""

    entity_description: AmpioSwitchEntityDescription

    def __init__(
        self,
        config: dict[str, Any],
        description: AmpioSwitchEntityDescription | None = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(config)

        # Get or create entity description
        device_class_str = config.get(CONF_DEVICE_CLASS)
        if description:
            self.entity_description = description
        elif device_class_str and device_class_str in SWITCH_DESCRIPTIONS:
            self.entity_description = SWITCH_DESCRIPTIONS[device_class_str]
        else:
            self.entity_description = DEFAULT_SWITCH_DESCRIPTION

        # Set device class from description
        self._attr_device_class = self.entity_description.device_class

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._state

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""

        @callback
        def state_message_received(msg: Any) -> None:
            """Handle new MQTT message."""
            self._state = self.parse_bool_state(msg.payload, self.name or "switch")
            self.async_write_ha_state()

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass,
            self._sub_state,
            self._create_topic_config(CONF_STATE_TOPIC, state_message_received),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.publish(self._config[CONF_COMMAND_TOPIC], SWITCH_CMD_OFF)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.publish(self._config[CONF_COMMAND_TOPIC], SWITCH_CMD_ON)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio switches from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][SWITCH_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioSwitch,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
