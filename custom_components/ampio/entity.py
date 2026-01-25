"""Ampio Entity base classes."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
    CONF_ICON,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import CONF_STATE_TOPIC, CONF_UNIQUE_ID, DATA_AMPIO, DATA_AMPIO_COORDINATOR, DEFAULT_QOS
from .mixins import StateMessageMixin

if TYPE_CHECKING:
    from .coordinator import AmpioCoordinator

_LOGGER = logging.getLogger(__name__)


class AmpioEntity(StateMessageMixin, Entity):
    """Base class for Ampio entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the entity."""
        self._config = config
        self._attr_unique_id = config.get(CONF_UNIQUE_ID)
        self._attr_device_class = config.get(CONF_DEVICE_CLASS)
        self._attr_icon = config.get(CONF_ICON)

        # Device info
        device_config = config.get(CONF_DEVICE)
        if device_config:
            self._attr_device_info = DeviceInfo(**device_config)

        # State
        self._state: Any = None
        self._sub_state: dict[str, Any] | None = None
        self._available = False

    def _create_topic_config(
        self,
        topic_key: str,
        callback: Callable[[Any], None],
        qos: int = DEFAULT_QOS,
    ) -> dict[str, Any]:
        """Create a topic subscription configuration.

        Args:
            topic_key: The config key for the topic (e.g., CONF_STATE_TOPIC)
            callback: The callback function to handle messages
            qos: Quality of service level

        Returns:
            Topic configuration dict, or empty dict if topic not configured
        """
        topic = self._config.get(topic_key)
        if not topic:
            return {}
        return {
            topic_key: {
                "topic": topic,
                "msg_callback": callback,
                "qos": qos,
            }
        }

    @property
    def coordinator(self) -> AmpioCoordinator | None:
        """Return the coordinator."""
        if self.hass is None:
            return None
        return self.hass.data.get(DATA_AMPIO, {}).get(DATA_AMPIO_COORDINATOR)

    @property
    def name(self) -> str | None:
        """Return the name of the entity.

        With has_entity_name=True, this becomes a suffix to the device name.
        Return None to use only the device name.
        """
        return self._config.get(CONF_FRIENDLY_NAME)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        state_topic = self._config.get(CONF_STATE_TOPIC)
        if state_topic:
            parts = state_topic.split("/")
            if len(parts) > 3:
                return {"ampio_topic": f"{parts[-4].lower()}/{parts[-2]}/{parts[-1]}"}
        return None

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics for this entity."""
        # Override in subclasses

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()
        await self.subscribe_topics()

        # Update entity name from config if not set
        entity_registry = er.async_get(self.hass)
        if self.registry_entry and self.registry_entry.name is None:
            friendly_name = self._config.get(CONF_FRIENDLY_NAME)
            if friendly_name:
                entity_registry.async_update_entity(self.entity_id, name=friendly_name)

        self._available = True

    def publish(
        self, topic: str, payload: str | bytes | int | float, qos: int = 0, retain: bool = False
    ) -> None:
        """Publish an MQTT message."""
        if self.coordinator:
            self.coordinator.publish(topic, payload, qos, retain)
