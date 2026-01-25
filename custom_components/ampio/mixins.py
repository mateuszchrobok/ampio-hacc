"""Ampio Entity mixins for common functionality."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)


class StateMessageMixin:
    """Mixin providing common state message parsing utilities."""

    @staticmethod
    @callback
    def parse_bool_state(payload: Any, entity_name: str = "entity") -> bool | None:
        """Parse a boolean state from MQTT payload.

        Args:
            payload: The MQTT message payload
            entity_name: Name for logging context

        Returns:
            Boolean state or None if parsing failed
        """
        try:
            return bool(int(payload))
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid boolean value for %s: %s", entity_name, payload)
            return None

    @staticmethod
    @callback
    def parse_int_state(
        payload: Any,
        entity_name: str = "entity",
        min_val: int | None = None,
        max_val: int | None = None,
    ) -> int | None:
        """Parse an integer state from MQTT payload.

        Args:
            payload: The MQTT message payload
            entity_name: Name for logging context
            min_val: Optional minimum valid value
            max_val: Optional maximum valid value

        Returns:
            Integer state or None if parsing failed
        """
        try:
            value = int(payload)
            if min_val is not None and value < min_val:
                _LOGGER.warning("Value %s below minimum %s for %s", value, min_val, entity_name)
                return None
            if max_val is not None and value > max_val:
                _LOGGER.warning("Value %s above maximum %s for %s", value, max_val, entity_name)
                return None
            return value
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid integer value for %s: %s", entity_name, payload)
            return None

    @staticmethod
    @callback
    def parse_float_state(payload: Any, entity_name: str = "entity") -> float | None:
        """Parse a float state from MQTT payload.

        Args:
            payload: The MQTT message payload
            entity_name: Name for logging context

        Returns:
            Float state or None if parsing failed
        """
        try:
            return float(payload)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid float value for %s: %s", entity_name, payload)
            return None

    @staticmethod
    @callback
    def parse_rgb_state(payload: Any, entity_name: str = "light") -> tuple[int, int, int] | None:
        """Parse RGB state from comma-separated MQTT payload.

        Args:
            payload: The MQTT message payload (e.g., "255,128,0")
            entity_name: Name for logging context

        Returns:
            Tuple of (R, G, B) values or None if parsing failed
        """
        try:
            rgb = list(map(int, payload.split(",")))
            if len(rgb) < 3:
                _LOGGER.warning(
                    "Invalid RGB format for %s: %s (expected 3 values)", entity_name, payload
                )
                return None
            return (rgb[0], rgb[1], rgb[2])
        except (ValueError, TypeError, AttributeError) as err:
            _LOGGER.warning(
                "Failed to parse RGB payload for %s '%s': %s", entity_name, payload, err
            )
            return None

    @staticmethod
    @callback
    def parse_rgbw_state(
        payload: Any, entity_name: str = "light"
    ) -> tuple[int, int, int, int] | None:
        """Parse RGBW state from comma-separated MQTT payload.

        Args:
            payload: The MQTT message payload (e.g., "255,128,0,255")
            entity_name: Name for logging context

        Returns:
            Tuple of (R, G, B, W) values or None if parsing failed
        """
        try:
            rgbw = list(map(int, payload.split(",")))
            if len(rgbw) < 4:
                _LOGGER.warning(
                    "Invalid RGBW format for %s: %s (expected 4 values)", entity_name, payload
                )
                return None
            return (rgbw[0], rgbw[1], rgbw[2], rgbw[3])
        except (ValueError, TypeError, AttributeError) as err:
            _LOGGER.warning(
                "Failed to parse RGBW payload for %s '%s': %s", entity_name, payload, err
            )
            return None
