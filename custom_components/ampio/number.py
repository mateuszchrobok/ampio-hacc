"""Ampio Number platform.

Exposes Ampio 8-bit analog flags (``afu8``) as writable numbers. They are the
one Ampio item type that is numeric, settable and has no ``/cmd`` topic: the
write is a raw CAN broadcast, so this platform builds the frame itself rather
than publishing a value to a per-item command topic.
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    DOMAIN as NUMBER_DOMAIN,
)
from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import discovery, subscription
from .const import (
    ANALOG_FLAG_MAX,
    ANALOG_FLAG_MIN,
    ANALOG_FLAG_STEP,
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_RAW_TOPIC,
    CONF_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity
from .models import analog_flag_raw_payload

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AmpioNumberEntityDescription(NumberEntityDescription):
    """Describes an Ampio number entity."""

    # No additional fields needed - we use the standard NumberEntityDescription fields


# Default description for the 8-bit analog flags. A flag is a raw register, so
# it carries no device class or unit, and a box beats a 0-255 slider.
DEFAULT_NUMBER_DESCRIPTION = AmpioNumberEntityDescription(
    key="analog_flag",
    mode=NumberMode.BOX,
    native_step=ANALOG_FLAG_STEP,
)


class AmpioNumber(AmpioEntity, NumberEntity):
    """Representation of an Ampio 8-bit analog flag."""

    entity_description: AmpioNumberEntityDescription

    def __init__(
        self,
        config: dict[str, Any],
        description: AmpioNumberEntityDescription | None = None,
    ) -> None:
        """Initialize the number."""
        super().__init__(config)

        self.entity_description = description or DEFAULT_NUMBER_DESCRIPTION

        # The raw topic is per-module, not per-item, so the flag index has to come
        # from the state topic -- the same way AmpioCover finds its channel.
        self._index: int | None = None
        state_topic = config.get(CONF_STATE_TOPIC)
        if state_topic:
            parts = state_topic.split("/")
            try:
                self._index = int(parts[-1])
            except (ValueError, IndexError):
                pass

        self._attr_native_min_value = config.get(CONF_MIN_VALUE, ANALOG_FLAG_MIN)
        self._attr_native_max_value = config.get(CONF_MAX_VALUE, ANALOG_FLAG_MAX)
        self._attr_native_step = self.entity_description.native_step
        self._attr_mode = self.entity_description.mode

    @property
    def native_value(self) -> float | None:
        """Return the current flag value."""
        return self._state

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""

        @callback
        def state_message_received(msg: Any) -> None:
            """Handle new MQTT message."""
            self._state = self.parse_int_state(
                msg.payload,
                self.name or "number",
                min_val=ANALOG_FLAG_MIN,
                max_val=ANALOG_FLAG_MAX,
            )
            self.async_write_ha_state()

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass,
            self._sub_state,
            self._create_topic_config(CONF_STATE_TOPIC, state_message_received),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)

    async def async_set_native_value(self, value: float) -> None:
        """Write the flag value as a raw CAN broadcast."""
        raw_topic = self._config.get(CONF_RAW_TOPIC)
        if raw_topic is None or self._index is None:
            _LOGGER.warning("Cannot set %s: no raw topic or no flag index", self.name or "number")
            return

        try:
            payload = analog_flag_raw_payload(int(value), self._index)
        except ValueError as err:
            _LOGGER.warning("Cannot set %s: %s", self.name or "number", err)
            return

        self.publish(raw_topic, payload)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio numbers from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][NUMBER_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioNumber,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
