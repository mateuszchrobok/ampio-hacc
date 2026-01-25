"""Ampio Cover platform."""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import discovery, subscription
from .const import (
    CONF_CLOSING_STATE_TOPIC,
    CONF_COMMAND_TOPIC,
    CONF_OPENING_STATE_TOPIC,
    CONF_RAW_TOPIC,
    CONF_STATE_TOPIC,
    CONF_TILT_POSITION_TOPIC,
    COVER_CMD_CLOSE,
    COVER_CMD_OPEN,
    COVER_CMD_STOP,
    COVER_MASK_BYTE,
    COVER_RAW_SET_POSITION,
    COVER_RAW_SET_TILT,
    COVER_TILT_CLOSED,
    COVER_TILT_KEEP_PREVIOUS,
    COVER_TILT_OPEN,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AmpioCoverEntityDescription(CoverEntityDescription):
    """Describes an Ampio cover entity."""

    # No additional fields needed - we use the standard CoverEntityDescription fields


# Map device class strings to CoverEntityDescription
COVER_DESCRIPTIONS: dict[str, AmpioCoverEntityDescription] = {
    "blind": AmpioCoverEntityDescription(
        key="blind",
        device_class=CoverDeviceClass.BLIND,
    ),
    "curtain": AmpioCoverEntityDescription(
        key="curtain",
        device_class=CoverDeviceClass.CURTAIN,
    ),
    "damper": AmpioCoverEntityDescription(
        key="damper",
        device_class=CoverDeviceClass.DAMPER,
    ),
    "door": AmpioCoverEntityDescription(
        key="door",
        device_class=CoverDeviceClass.DOOR,
    ),
    "garage": AmpioCoverEntityDescription(
        key="garage",
        device_class=CoverDeviceClass.GARAGE,
    ),
    "gate": AmpioCoverEntityDescription(
        key="gate",
        device_class=CoverDeviceClass.GATE,
    ),
    "shade": AmpioCoverEntityDescription(
        key="shade",
        device_class=CoverDeviceClass.SHADE,
    ),
    "shutter": AmpioCoverEntityDescription(
        key="shutter",
        device_class=CoverDeviceClass.SHUTTER,
    ),
    "awning": AmpioCoverEntityDescription(
        key="awning",
        device_class=CoverDeviceClass.AWNING,
    ),
    "window": AmpioCoverEntityDescription(
        key="window",
        device_class=CoverDeviceClass.WINDOW,
    ),
}

# Default description for covers without a specific device class
DEFAULT_COVER_DESCRIPTION = AmpioCoverEntityDescription(
    key="generic",
    device_class=CoverDeviceClass.SHUTTER,
)


class AmpioCover(AmpioEntity, RestoreEntity, CoverEntity):
    """Representation of an Ampio Cover."""

    entity_description: AmpioCoverEntityDescription

    def __init__(
        self,
        config: dict[str, Any],
        description: AmpioCoverEntityDescription | None = None,
    ) -> None:
        """Initialize the cover."""
        super().__init__(config)

        self._cover_position: int | None = None
        self._tilt_position: int | None = None
        self._opening: bool | None = None
        self._closing: bool | None = None
        self._index: int | None = None

        # Extract index from state topic
        state_topic = config.get(CONF_STATE_TOPIC)
        if state_topic:
            parts = state_topic.split("/")
            try:
                self._index = int(parts[-1])
            except (ValueError, IndexError):
                pass

        # Get or create entity description
        device_class_str = config.get(CONF_DEVICE_CLASS)
        if description:
            self.entity_description = description
        elif device_class_str and device_class_str in COVER_DESCRIPTIONS:
            self.entity_description = COVER_DESCRIPTIONS[device_class_str]
        else:
            self.entity_description = DEFAULT_COVER_DESCRIPTION

        # Set device class from description
        self._attr_device_class = self.entity_description.device_class

        # Set supported features
        features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

        # Add tilt features if tilt topic is configured
        if config.get(CONF_TILT_POSITION_TOPIC):
            features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.STOP_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )

        self._attr_supported_features = features

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover (0 closed, 100 open)."""
        return self._cover_position

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current tilt position of cover."""
        return self._tilt_position

    @property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening."""
        return self._opening

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing."""
        return self._closing

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        is_closed = True
        if self._cover_position is not None:
            is_closed = self._cover_position == 0
        if self._tilt_position is not None:
            is_closed = is_closed and self._tilt_position == 0
        return is_closed

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""
        topics: dict[str, dict[str, Any]] = {}

        @callback
        def position_received(msg: Any) -> None:
            """Handle position message."""
            try:
                self._cover_position = int(msg.payload)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid cover position: %s", msg.payload)
                return
            self.async_write_ha_state()

        if self._config.get(CONF_STATE_TOPIC):
            topics[CONF_STATE_TOPIC] = {
                "topic": self._config[CONF_STATE_TOPIC],
                "msg_callback": position_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        def tilt_received(msg: Any) -> None:
            """Handle tilt position message."""
            try:
                self._tilt_position = int(msg.payload)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid tilt position: %s", msg.payload)
                return
            self.async_write_ha_state()

        if self._config.get(CONF_TILT_POSITION_TOPIC):
            topics[CONF_TILT_POSITION_TOPIC] = {
                "topic": self._config[CONF_TILT_POSITION_TOPIC],
                "msg_callback": tilt_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        def closing_received(msg: Any) -> None:
            """Handle closing state message."""
            try:
                self._closing = bool(int(msg.payload))
            except (ValueError, TypeError):
                return
            self.async_write_ha_state()

        if self._config.get(CONF_CLOSING_STATE_TOPIC):
            topics[CONF_CLOSING_STATE_TOPIC] = {
                "topic": self._config[CONF_CLOSING_STATE_TOPIC],
                "msg_callback": closing_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        def opening_received(msg: Any) -> None:
            """Handle opening state message."""
            try:
                self._opening = bool(int(msg.payload))
            except (ValueError, TypeError):
                return
            self.async_write_ha_state()

        if self._config.get(CONF_OPENING_STATE_TOPIC):
            topics[CONF_OPENING_STATE_TOPIC] = {
                "topic": self._config[CONF_OPENING_STATE_TOPIC],
                "msg_callback": opening_received,
                "qos": DEFAULT_QOS,
            }

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass, self._sub_state, topics
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = last_state.state
            if ATTR_CURRENT_POSITION in last_state.attributes:
                self._cover_position = last_state.attributes[ATTR_CURRENT_POSITION]
            if ATTR_CURRENT_TILT_POSITION in last_state.attributes:
                self._tilt_position = last_state.attributes[ATTR_CURRENT_TILT_POSITION]

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self.publish(self._config[CONF_COMMAND_TOPIC], COVER_CMD_OPEN)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self.publish(self._config[CONF_COMMAND_TOPIC], COVER_CMD_CLOSE)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        self.publish(self._config[CONF_COMMAND_TOPIC], COVER_CMD_STOP)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get("position")
        if position is None or self._index is None:
            return

        position_byte = (COVER_MASK_BYTE & position).to_bytes(1, byteorder="little")
        mask = COVER_MASK_BYTE & (0x01 << (self._index - 1))
        mask_byte = mask.to_bytes(1, byteorder="little")
        tilt_byte = COVER_TILT_KEEP_PREVIOUS.to_bytes(1, byteorder="little")
        raw = COVER_RAW_SET_POSITION + mask_byte + position_byte + tilt_byte
        self.publish(self._config[CONF_RAW_TOPIC], raw.hex())

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        if self._index is None:
            return

        position_byte = COVER_TILT_OPEN.to_bytes(1, byteorder="little")
        mask = COVER_MASK_BYTE & (0x01 << (self._index - 1))
        mask_byte = mask.to_bytes(1, byteorder="little")
        raw = COVER_RAW_SET_TILT + mask_byte + position_byte
        self.publish(self._config[CONF_RAW_TOPIC], raw.hex())

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        if self._index is None:
            return

        position_byte = COVER_TILT_CLOSED.to_bytes(1, byteorder="little")
        mask = COVER_MASK_BYTE & (0x01 << (self._index - 1))
        mask_byte = mask.to_bytes(1, byteorder="little")
        raw = COVER_RAW_SET_TILT + mask_byte + position_byte
        self.publish(self._config[CONF_RAW_TOPIC], raw.hex())

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        position = kwargs.get("tilt_position")
        if position is None or self._index is None:
            return

        position_byte = (COVER_MASK_BYTE & position).to_bytes(1, byteorder="little")
        mask = COVER_MASK_BYTE & (0x01 << (self._index - 1))
        mask_byte = mask.to_bytes(1, byteorder="little")
        raw = COVER_RAW_SET_TILT + mask_byte + position_byte
        self.publish(self._config[CONF_RAW_TOPIC], raw.hex())

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the cover tilt."""
        self.publish(self._config[CONF_COMMAND_TOPIC], COVER_CMD_STOP)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio covers from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][COVER_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioCover,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
