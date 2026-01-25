"""Ampio Climate platform."""

from __future__ import annotations

import functools
import logging
from typing import Any

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import discovery, subscription
from .const import (
    AMPIO_CLIMATE_MODE_BLOCK,
    AMPIO_CLIMATE_MODE_CALENDAR,
    AMPIO_CLIMATE_MODE_HOLIDAYS,
    AMPIO_CLIMATE_MODE_MANUAL_DAY,
    AMPIO_CLIMATE_MODE_MANUAL_NIGHT,
    CONF_MODE_COMMAND_TOPIC,
    CONF_MODE_STATE_TOPIC,
    CONF_SETPOINT_COMMAND_TOPIC,
    CONF_SETPOINT_STATE_TOPIC,
    CONF_TEMPERATURE_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)

# Ampio mode to HVAC mode mapping
AMPIO_MODE_TO_HVAC: dict[int, HVACMode] = {
    AMPIO_CLIMATE_MODE_CALENDAR: HVACMode.AUTO,
    AMPIO_CLIMATE_MODE_MANUAL_DAY: HVACMode.HEAT,
    AMPIO_CLIMATE_MODE_MANUAL_NIGHT: HVACMode.HEAT,
    AMPIO_CLIMATE_MODE_HOLIDAYS: HVACMode.AUTO,
    AMPIO_CLIMATE_MODE_BLOCK: HVACMode.OFF,
}

# HVAC mode to Ampio mode mapping (default mappings)
HVAC_TO_AMPIO_MODE: dict[HVACMode, int] = {
    HVACMode.AUTO: AMPIO_CLIMATE_MODE_CALENDAR,
    HVACMode.HEAT: AMPIO_CLIMATE_MODE_MANUAL_DAY,
    HVACMode.OFF: AMPIO_CLIMATE_MODE_BLOCK,
}

# Preset modes
PRESET_CALENDAR = "calendar"
PRESET_MANUAL_DAY = "manual_day"
PRESET_MANUAL_NIGHT = "manual_night"
PRESET_HOLIDAYS = "holidays"
PRESET_BLOCK = "block"

AMPIO_MODE_TO_PRESET: dict[int, str] = {
    AMPIO_CLIMATE_MODE_CALENDAR: PRESET_CALENDAR,
    AMPIO_CLIMATE_MODE_MANUAL_DAY: PRESET_MANUAL_DAY,
    AMPIO_CLIMATE_MODE_MANUAL_NIGHT: PRESET_MANUAL_NIGHT,
    AMPIO_CLIMATE_MODE_HOLIDAYS: PRESET_HOLIDAYS,
    AMPIO_CLIMATE_MODE_BLOCK: PRESET_BLOCK,
}

PRESET_TO_AMPIO_MODE: dict[str, int] = {
    PRESET_CALENDAR: AMPIO_CLIMATE_MODE_CALENDAR,
    PRESET_MANUAL_DAY: AMPIO_CLIMATE_MODE_MANUAL_DAY,
    PRESET_MANUAL_NIGHT: AMPIO_CLIMATE_MODE_MANUAL_NIGHT,
    PRESET_HOLIDAYS: AMPIO_CLIMATE_MODE_HOLIDAYS,
    PRESET_BLOCK: AMPIO_CLIMATE_MODE_BLOCK,
}


class AmpioClimate(AmpioEntity, RestoreEntity, ClimateEntity):
    """Representation of an Ampio Climate entity.

    Supports MRT-16s temperature controllers with:
    - Temperature reading from temperature sensors
    - Setpoint control via rs/<nr>/cmd
    - Mode control via rm/<nr>/cmd (0=calendar, 1=manual day, 2=manual night, 3=holidays, 4=block)
    """

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_preset_modes = list(PRESET_TO_AMPIO_MODE.keys())
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = -20.0
    _attr_max_temp = 50.0

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the climate entity."""
        super().__init__(config)

        self._current_temperature: float | None = None
        self._target_temperature: float | None = None
        self._ampio_mode: int = AMPIO_CLIMATE_MODE_CALENDAR

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        return AMPIO_MODE_TO_HVAC.get(self._ampio_mode, HVACMode.AUTO)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action.

        Determine based on temperature difference.
        """
        if self._ampio_mode == AMPIO_CLIMATE_MODE_BLOCK:
            return HVACAction.OFF

        if self._current_temperature is not None and self._target_temperature is not None:
            if self._current_temperature < self._target_temperature - 0.5:
                return HVACAction.HEATING
            return HVACAction.IDLE

        return None

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return AMPIO_MODE_TO_PRESET.get(self._ampio_mode)

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""

        @callback
        def temperature_received(msg: Any) -> None:
            """Handle temperature MQTT message."""
            try:
                self._current_temperature = float(msg.payload)
            except (ValueError, TypeError):
                self._current_temperature = None
                _LOGGER.warning("Invalid temperature value: %s", msg.payload)
            self.async_write_ha_state()

        @callback
        def setpoint_received(msg: Any) -> None:
            """Handle setpoint MQTT message."""
            try:
                self._target_temperature = float(msg.payload)
            except (ValueError, TypeError):
                self._target_temperature = None
                _LOGGER.warning("Invalid setpoint value: %s", msg.payload)
            self.async_write_ha_state()

        @callback
        def mode_received(msg: Any) -> None:
            """Handle mode MQTT message."""
            try:
                self._ampio_mode = int(msg.payload)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid mode value: %s", msg.payload)
            self.async_write_ha_state()

        topics: dict[str, dict[str, Any]] = {}

        if CONF_TEMPERATURE_STATE_TOPIC in self._config:
            topics["temperature_topic"] = {
                "topic": self._config[CONF_TEMPERATURE_STATE_TOPIC],
                "msg_callback": temperature_received,
                "qos": DEFAULT_QOS,
            }

        if CONF_SETPOINT_STATE_TOPIC in self._config:
            topics["setpoint_topic"] = {
                "topic": self._config[CONF_SETPOINT_STATE_TOPIC],
                "msg_callback": setpoint_received,
                "qos": DEFAULT_QOS,
            }

        if CONF_MODE_STATE_TOPIC in self._config:
            topics["mode_topic"] = {
                "topic": self._config[CONF_MODE_STATE_TOPIC],
                "msg_callback": mode_received,
                "qos": DEFAULT_QOS,
            }

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass,
            self._sub_state,
            topics,
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            # Restore target temperature
            if last_state.attributes.get(ATTR_TEMPERATURE) is not None:
                try:
                    self._target_temperature = float(last_state.attributes[ATTR_TEMPERATURE])
                except (ValueError, TypeError):
                    pass

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Clamp to valid range
        temperature = max(self._attr_min_temp, min(self._attr_max_temp, temperature))

        # Publish setpoint command
        if CONF_SETPOINT_COMMAND_TOPIC in self._config:
            self.publish(self._config[CONF_SETPOINT_COMMAND_TOPIC], f"{temperature:.1f}")
            self._target_temperature = temperature
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        ampio_mode = HVAC_TO_AMPIO_MODE.get(hvac_mode)
        if ampio_mode is None:
            _LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)
            return

        if CONF_MODE_COMMAND_TOPIC in self._config:
            self.publish(self._config[CONF_MODE_COMMAND_TOPIC], str(ampio_mode))
            self._ampio_mode = ampio_mode
            self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        ampio_mode = PRESET_TO_AMPIO_MODE.get(preset_mode)
        if ampio_mode is None:
            _LOGGER.warning("Unsupported preset mode: %s", preset_mode)
            return

        if CONF_MODE_COMMAND_TOPIC in self._config:
            self.publish(self._config[CONF_MODE_COMMAND_TOPIC], str(ampio_mode))
            self._ampio_mode = ampio_mode
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio climate entities from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][CLIMATE_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioClimate,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
