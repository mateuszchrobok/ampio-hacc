"""Ampio Event platform for button press, RFID, and gesture events."""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.event import DOMAIN as EVENT_DOMAIN
from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_CLASS, CONF_FRIENDLY_NAME, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import discovery, subscription
from .const import (
    CONF_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)

# Event types for Ampio devices
EVENT_BUTTON_PRESS = "button_press"
EVENT_BUTTON_RELEASE = "button_release"
EVENT_BUTTON_LONG_PRESS = "button_long_press"
EVENT_BUTTON_DOUBLE_PRESS = "button_double_press"
EVENT_RFID_SCAN = "rfid_scan"
EVENT_GESTURE_SWIPE_LEFT = "gesture_swipe_left"
EVENT_GESTURE_SWIPE_RIGHT = "gesture_swipe_right"
EVENT_GESTURE_SWIPE_UP = "gesture_swipe_up"
EVENT_GESTURE_SWIPE_DOWN = "gesture_swipe_down"
EVENT_GESTURE_TAP = "gesture_tap"
EVENT_GESTURE_DOUBLE_TAP = "gesture_double_tap"


@dataclass(frozen=True, kw_only=True)
class AmpioEventEntityDescription(EventEntityDescription):
    """Describes an Ampio event entity."""


# Map device class strings to EventEntityDescription
EVENT_DESCRIPTIONS: dict[str, AmpioEventEntityDescription] = {
    "button": AmpioEventEntityDescription(
        key="button",
        device_class=EventDeviceClass.BUTTON,
        event_types=[
            EVENT_BUTTON_PRESS,
            EVENT_BUTTON_RELEASE,
            EVENT_BUTTON_LONG_PRESS,
            EVENT_BUTTON_DOUBLE_PRESS,
        ],
    ),
    "doorbell": AmpioEventEntityDescription(
        key="doorbell",
        device_class=EventDeviceClass.DOORBELL,
        event_types=[EVENT_BUTTON_PRESS],
    ),
    "motion": AmpioEventEntityDescription(
        key="motion",
        device_class=EventDeviceClass.MOTION,
        event_types=[EVENT_BUTTON_PRESS, EVENT_BUTTON_RELEASE],
    ),
}

# Default description for unknown event types
DEFAULT_EVENT_DESCRIPTION = AmpioEventEntityDescription(
    key="unknown",
    event_types=[EVENT_BUTTON_PRESS, EVENT_BUTTON_RELEASE],
)


class AmpioEvent(AmpioEntity, EventEntity):
    """Representation of an Ampio Event entity."""

    entity_description: AmpioEventEntityDescription
    _sub_state: dict[str, Any] | None = None

    def __init__(
        self,
        config: dict[str, Any],
        description: AmpioEventEntityDescription | None = None,
    ) -> None:
        """Initialize the event entity."""
        super().__init__(config)

        # Get or create entity description
        device_class_str = config.get(CONF_DEVICE_CLASS)
        if description:
            self.entity_description = description
        elif device_class_str and device_class_str in EVENT_DESCRIPTIONS:
            self.entity_description = EVENT_DESCRIPTIONS[device_class_str]
        else:
            self.entity_description = DEFAULT_EVENT_DESCRIPTION

        # Set attributes from description
        self._attr_device_class = self.entity_description.device_class
        self._attr_event_types = self.entity_description.event_types
        self._attr_name = config.get(CONF_FRIENDLY_NAME) or config.get(CONF_NAME)

        # Track last state to detect transitions
        self._last_state: int | None = None

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""

        @callback
        def state_message_received(msg: Any) -> None:
            """Handle new MQTT message for event detection."""
            try:
                payload_str = (
                    msg.payload.decode() if isinstance(msg.payload, bytes) else str(msg.payload)
                )
                new_state = int(payload_str)
            except (ValueError, TypeError, AttributeError):
                _LOGGER.warning("Invalid event value: %s", msg.payload)
                return

            # Detect state transitions for button events
            if self._last_state is not None:
                if self._last_state == 0 and new_state == 1:
                    # Button pressed (0 -> 1)
                    self._fire_event(EVENT_BUTTON_PRESS)
                elif self._last_state == 1 and new_state == 0:
                    # Button released (1 -> 0)
                    self._fire_event(EVENT_BUTTON_RELEASE)
            elif new_state == 1:
                # First time seeing state 1, trigger press
                self._fire_event(EVENT_BUTTON_PRESS)

            self._last_state = new_state

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass,
            self._sub_state,
            {
                "state_topic": {
                    "topic": self._config[CONF_STATE_TOPIC],
                    "msg_callback": state_message_received,
                    "qos": DEFAULT_QOS,
                }
            },
        )

    def _fire_event(self, event_type: str, event_attributes: dict[str, Any] | None = None) -> None:
        """Fire an event."""
        if event_type in self._attr_event_types:
            self._trigger_event(event_type, event_attributes or {})
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe when added to hass."""
        await super().async_added_to_hass()
        await self.subscribe_topics()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio events from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO].get(EVENT_DOMAIN, [])

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioEvent,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
