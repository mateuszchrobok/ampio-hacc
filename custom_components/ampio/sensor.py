"""Ampio Sensor platform."""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    CONF_DEVICE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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


@dataclass(frozen=True, kw_only=True)
class AmpioSensorEntityDescription(SensorEntityDescription):
    """Describes an Ampio sensor entity."""

    # No additional fields needed - we use the standard SensorEntityDescription fields


# Map device class strings to SensorEntityDescription
SENSOR_DESCRIPTIONS: dict[str, AmpioSensorEntityDescription] = {
    "temperature": AmpioSensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "humidity": AmpioSensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "pressure": AmpioSensorEntityDescription(
        key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "illuminance": AmpioSensorEntityDescription(
        key="illuminance",
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "signal_strength": AmpioSensorEntityDescription(
        key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "aqi": AmpioSensorEntityDescription(
        key="aqi",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "carbon_dioxide": AmpioSensorEntityDescription(
        key="carbon_dioxide",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Energy/pulse counter sensors
    "energy": AmpioSensorEntityDescription(
        key="energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "gas": AmpioSensorEntityDescription(
        key="gas",
        device_class=SensorDeviceClass.GAS,
        native_unit_of_measurement="m³",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "water": AmpioSensorEntityDescription(
        key="water",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement="m³",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Battery level for wireless modules
    "battery": AmpioSensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Analog input sensors (0-10V / 4-20mA)
    "voltage": AmpioSensorEntityDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "current": AmpioSensorEntityDescription(
        key="current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement="mA",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Wind speed for METEO modules
    "wind_speed": AmpioSensorEntityDescription(
        key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement="m/s",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Precipitation for METEO modules
    "precipitation": AmpioSensorEntityDescription(
        key="precipitation",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement="mm",
        state_class=SensorStateClass.MEASUREMENT,
    ),
}

# Fallback description for unknown sensor types
DEFAULT_SENSOR_DESCRIPTION = AmpioSensorEntityDescription(
    key="unknown",
    state_class=SensorStateClass.MEASUREMENT,
)


class AmpioSensor(AmpioEntity, RestoreEntity, SensorEntity):
    """Representation of an Ampio Sensor."""

    entity_description: AmpioSensorEntityDescription

    def __init__(
        self,
        config: dict[str, Any],
        description: AmpioSensorEntityDescription | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(config)

        # Get or create entity description
        device_class_str = config.get(CONF_DEVICE_CLASS)
        if description:
            self.entity_description = description
        elif device_class_str and device_class_str in SENSOR_DESCRIPTIONS:
            self.entity_description = SENSOR_DESCRIPTIONS[device_class_str]
        else:
            self.entity_description = DEFAULT_SENSOR_DESCRIPTION

        # Override unit if specified in config (for backwards compatibility)
        config_unit = config.get(CONF_UNIT_OF_MEASUREMENT)
        if config_unit and config_unit != self.entity_description.native_unit_of_measurement:
            self._attr_native_unit_of_measurement = config_unit
        else:
            self._attr_native_unit_of_measurement = (
                self.entity_description.native_unit_of_measurement
            )

        # Set device class from description
        self._attr_device_class = self.entity_description.device_class
        self._attr_state_class = self.entity_description.state_class
        self._attr_entity_category = self.entity_description.entity_category

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        return self._state

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""

        @callback
        def state_message_received(msg: Any) -> None:
            """Handle new MQTT message."""
            try:
                self._state = float(msg.payload)
            except (ValueError, TypeError):
                self._state = None
                _LOGGER.warning("Invalid sensor value: %s", msg.payload)

            self.async_write_ha_state()

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

    async def async_added_to_hass(self) -> None:
        """Restore last state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = float(last_state.state)
            except (ValueError, TypeError):
                pass

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio sensors from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][SENSOR_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioSensor,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
