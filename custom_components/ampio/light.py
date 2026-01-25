"""Ampio Light platform."""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import Any

import homeassistant.util.color as color_util
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import discovery, subscription
from .const import (
    CONF_BRIGHTNESS_COMMAND_TOPIC,
    CONF_BRIGHTNESS_STATE_TOPIC,
    CONF_COMMAND_TOPIC,
    CONF_RGB_COMMAND_TOPIC,
    CONF_RGB_STATE_TOPIC,
    CONF_STATE_TOPIC,
    CONF_WHITE_VALUE_COMMAND_TOPIC,
    CONF_WHITE_VALUE_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    LIGHT_CMD_OFF,
    LIGHT_RGB_OFF,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AmpioLightEntityDescription(LightEntityDescription):
    """Describes an Ampio light entity."""

    # No additional fields needed - color modes are determined from config


# Default description for all lights
DEFAULT_LIGHT_DESCRIPTION = AmpioLightEntityDescription(
    key="light",
)


class AmpioLight(AmpioEntity, LightEntity):
    """Representation of an Ampio Light."""

    entity_description: AmpioLightEntityDescription

    def __init__(
        self,
        config: dict[str, Any],
        description: AmpioLightEntityDescription | None = None,
    ) -> None:
        """Initialize the light."""
        super().__init__(config)

        self._brightness: int | None = None
        self._hs: tuple[float, float] | None = None
        self._white_value: float | None = None

        # Set entity description
        self.entity_description = description or DEFAULT_LIGHT_DESCRIPTION

        # Determine supported color modes from config
        self._attr_supported_color_modes = self._determine_color_modes()

    def _determine_color_modes(self) -> set[ColorMode]:
        """Determine supported color modes from configuration."""
        modes: set[ColorMode] = set()
        if self._config.get(CONF_RGB_COMMAND_TOPIC):
            modes.add(ColorMode.HS)
        if self._config.get(CONF_WHITE_VALUE_COMMAND_TOPIC):
            modes.add(ColorMode.WHITE)
        if self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC) and not modes:
            modes.add(ColorMode.BRIGHTNESS)
        if not modes:
            modes.add(ColorMode.ONOFF)
        return modes

    @property
    def color_mode(self) -> ColorMode | None:
        """Return the current color mode."""
        if self._hs and any(self._hs):
            return ColorMode.HS
        if self._white_value:
            return ColorMode.WHITE
        if self._brightness:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light (0-255)."""
        if self._brightness:
            return min(round(self._brightness), 255)
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value."""
        return self._hs

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""
        topics: dict[str, dict[str, Any]] = {}

        @callback
        def state_received(msg: Any) -> None:
            """Handle state message."""
            try:
                self._state = bool(int(msg.payload))
            except (ValueError, TypeError):
                return
            self.async_write_ha_state()

        if self._config.get(CONF_STATE_TOPIC):
            topics[CONF_STATE_TOPIC] = {
                "topic": self._config[CONF_STATE_TOPIC],
                "msg_callback": state_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        def brightness_received(msg: Any) -> None:
            """Handle brightness message."""
            try:
                brightness = int(msg.payload)
            except (ValueError, TypeError):
                return
            if brightness > 0:
                self._brightness = brightness
                self._state = True
                self.async_write_ha_state()

        if self._config.get(CONF_BRIGHTNESS_STATE_TOPIC):
            topics[CONF_BRIGHTNESS_STATE_TOPIC] = {
                "topic": self._config[CONF_BRIGHTNESS_STATE_TOPIC],
                "msg_callback": brightness_received,
                "qos": DEFAULT_QOS,
            }
            self._brightness = 255
        elif self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC):
            self._brightness = 255

        @callback
        def rgb_received(msg: Any) -> None:
            """Handle RGB message."""
            rgb = self.parse_rgb_state(msg.payload, self.name or "light")
            if rgb is None:
                return

            if any(rgb):
                self._hs = color_util.color_RGB_to_hs(*rgb[:3])
                percent_bright = float(color_util.color_RGB_to_hsv(*rgb[:3])[2]) / 100.0
                self._brightness = int(percent_bright * 255)
                self._state = True
            else:
                self._state = False

            self.async_write_ha_state()

        if self._config.get(CONF_RGB_STATE_TOPIC):
            topics[CONF_RGB_STATE_TOPIC] = {
                "topic": self._config[CONF_RGB_STATE_TOPIC],
                "msg_callback": rgb_received,
                "qos": DEFAULT_QOS,
            }
            self._hs = (0, 0)
        elif self._config.get(CONF_RGB_COMMAND_TOPIC):
            self._hs = (0, 0)

        @callback
        def white_value_received(msg: Any) -> None:
            """Handle white value message."""
            try:
                self._white_value = float(msg.payload)
            except (ValueError, TypeError):
                return
            if self._white_value > 0:
                self._state = True
            self.async_write_ha_state()

        if self._config.get(CONF_WHITE_VALUE_STATE_TOPIC):
            topics[CONF_WHITE_VALUE_STATE_TOPIC] = {
                "topic": self._config.get(CONF_WHITE_VALUE_STATE_TOPIC),
                "msg_callback": white_value_received,
                "qos": DEFAULT_QOS,
            }
            self._white_value = 255
        elif self._config.get(CONF_WHITE_VALUE_COMMAND_TOPIC):
            self._white_value = 255

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass, self._sub_state, topics
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if self._config.get(CONF_RGB_COMMAND_TOPIC):
            self.publish(self._config[CONF_RGB_COMMAND_TOPIC], LIGHT_RGB_OFF)
        else:
            self.publish(self._config[CONF_COMMAND_TOPIC], LIGHT_CMD_OFF)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if ATTR_BRIGHTNESS not in kwargs:
            kwargs[ATTR_BRIGHTNESS] = self._brightness or 255

        # Handle HS color
        if ATTR_HS_COLOR in kwargs and self._config.get(CONF_RGB_COMMAND_TOPIC):
            hs_color = kwargs[ATTR_HS_COLOR]
            if self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC):
                brightness = 255
            else:
                brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness or 255)

            rgb = color_util.color_hsv_to_RGB(hs_color[0], hs_color[1], brightness / 255 * 100)
            rgb_str = ",".join(map(str, rgb))
            self.publish(self._config[CONF_RGB_COMMAND_TOPIC], rgb_str)

        # Handle brightness
        if ATTR_BRIGHTNESS in kwargs and self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC):
            brightness_normalized = kwargs[ATTR_BRIGHTNESS] / 255
            device_brightness = max(1, min(round(brightness_normalized * 255), 255))
            self.publish(self._config[CONF_BRIGHTNESS_COMMAND_TOPIC], device_brightness)

        # Handle brightness via RGB when no dedicated brightness topic
        elif (
            ATTR_BRIGHTNESS in kwargs
            and ATTR_HS_COLOR not in kwargs
            and self._config.get(CONF_RGB_COMMAND_TOPIC)
            and self._hs
        ):
            rgb = color_util.color_hsv_to_RGB(
                self._hs[0], self._hs[1], kwargs[ATTR_BRIGHTNESS] / 255 * 100
            )
            rgb_str = ",".join(map(str, rgb))
            self.publish(self._config[CONF_RGB_COMMAND_TOPIC], rgb_str)

        # Handle white value
        if ATTR_WHITE in kwargs and self._config.get(CONF_WHITE_VALUE_COMMAND_TOPIC):
            percent_white = float(kwargs[ATTR_WHITE]) / 255
            device_white_value = min(round(percent_white * 255), 255)
            self.publish(self._config[CONF_WHITE_VALUE_COMMAND_TOPIC], device_white_value)

        # Simple on/off command
        if self._config.get(CONF_COMMAND_TOPIC):
            self.publish(self._config[CONF_COMMAND_TOPIC], kwargs[ATTR_BRIGHTNESS])


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio lights from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][LIGHT_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioLight,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
