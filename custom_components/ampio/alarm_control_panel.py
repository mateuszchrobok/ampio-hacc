"""Ampio Alarm Control Panel platform."""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_DOMAIN,
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import discovery, subscription
from .const import (
    ALARM_CMD_ARM,
    ALARM_CMD_CLEAR,
    ALARM_CMD_DISARM,
    CONF_ALARM_TOPIC,
    CONF_ARMED_TOPIC,
    CONF_AWAY_ZONES,
    CONF_ENTRYTIME_TOPIC,
    CONF_EXITTIME10_TOPIC,
    CONF_EXITTIME_TOPIC,
    CONF_HOME_ZONES,
    CONF_RAW_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
    ZONE_BITMASK,
)
from .entity import AmpioEntity
from .models import IndexIntData

_LOGGER = logging.getLogger(__name__)


class AmpioSatelAlarmControlPanel(AmpioEntity, AlarmControlPanelEntity):
    """Representation of an Ampio Satel Alarm Control Panel."""

    _attr_code_arm_required = False

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the alarm control panel."""
        super().__init__(config)

        self._alarm_state = STATE_UNKNOWN
        self._armed: set[int] = set()
        self._alarm: set[int] = set()
        self._exittime: set[int] = set()
        self._exittime10: set[int] = set()
        self._entrytime: set[int] = set()

        self._home_zones: set[int] = set()
        self._home_cmd_data: str | None = None
        self._away_zones: set[int] = set()
        self._away_cmd_data: str | None = None
        self._all_cmd_data: str | None = None

        # Build supported features and zone masks
        features = AlarmControlPanelEntityFeature(0)

        if CONF_AWAY_ZONES in self._config:
            self._away_zones = self._config[CONF_AWAY_ZONES]
            features |= AlarmControlPanelEntityFeature.ARM_AWAY
            self._away_cmd_data = self._build_zone_mask(self._away_zones)

        if CONF_HOME_ZONES in self._config:
            self._home_zones = self._config[CONF_HOME_ZONES]
            features |= AlarmControlPanelEntityFeature.ARM_HOME
            self._home_cmd_data = self._build_zone_mask(self._home_zones)

        self._attr_supported_features = features

        # Build all zones mask for disarm
        all_zones = self._home_zones | self._away_zones
        self._all_cmd_data = self._build_zone_mask(all_zones)

    @staticmethod
    def _build_zone_mask(zones: set[int]) -> str:
        """Build zone bitmask as hex string."""
        mask = 0
        for zone in zones:
            mask |= (0x01 << (zone - 1)) & ZONE_BITMASK
        return mask.to_bytes(4, byteorder="little").hex()

    def _is_armed_away(self) -> bool:
        """Check if all away zones are armed."""
        return bool(self._away_zones) and self._away_zones == (self._armed & self._away_zones)

    def _is_armed_home(self) -> bool:
        """Check if all home zones are armed."""
        return bool(self._home_zones) and self._home_zones == (self._armed & self._home_zones)

    def _is_triggered(self) -> bool:
        """Check if alarm is triggered."""
        return bool(self._alarm)

    def _is_arming(self) -> bool:
        """Check if alarm is in arming state (exit time active)."""
        return bool(self._exittime or self._exittime10)

    def _is_pending(self) -> bool:
        """Check if alarm is pending (entry time active)."""
        return bool(self._entrytime)

    def _is_disarmed(self) -> bool:
        """Check if alarm is fully disarmed."""
        return not any(
            (
                self._armed,
                self._alarm,
                self._exittime,
                self._exittime10,
                self._entrytime,
            )
        )

    @property
    def state(self) -> str:
        """Return the state of the alarm."""
        if self._is_armed_away():
            self._alarm_state = AlarmControlPanelState.ARMED_AWAY
        elif self._is_armed_home():
            self._alarm_state = AlarmControlPanelState.ARMED_HOME
        elif self._is_triggered():
            self._alarm_state = AlarmControlPanelState.TRIGGERED
        elif self._is_arming():
            self._alarm_state = AlarmControlPanelState.ARMING
        elif self._is_pending():
            self._alarm_state = AlarmControlPanelState.PENDING
        elif self._is_disarmed():
            self._alarm_state = AlarmControlPanelState.DISARMED

        return self._alarm_state

    async def subscribe_topics(self) -> None:
        """Subscribe to MQTT topics."""
        topics: dict[str, dict[str, Any]] = {}

        @callback
        def armed_message_received(msg: Any) -> None:
            """Handle armed state message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Unable to parse armed MQTT message")
                return

            if data.value == 1:
                self._armed.add(data.index)
            else:
                self._armed.discard(data.index)

            _LOGGER.debug("Armed: %s", self._armed)
            self.async_write_ha_state()

        topics[CONF_ARMED_TOPIC] = {
            "topic": self._config[CONF_ARMED_TOPIC],
            "msg_callback": armed_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def alarm_message_received(msg: Any) -> None:
            """Handle alarm triggered message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Unable to parse alarm MQTT message")
                return

            if data.value == 1:
                self._alarm.add(data.index)
            else:
                self._alarm.discard(data.index)

            _LOGGER.debug("Alarm: %s", self._alarm)
            self.async_write_ha_state()

        topics[CONF_ALARM_TOPIC] = {
            "topic": self._config[CONF_ALARM_TOPIC],
            "msg_callback": alarm_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def entrytime_message_received(msg: Any) -> None:
            """Handle entry time message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Unable to parse entry time MQTT message")
                return

            if data.value == 1:
                self._entrytime.add(data.index)
            else:
                self._entrytime.discard(data.index)

            _LOGGER.debug("Entry Time: %s", self._entrytime)
            self.async_write_ha_state()

        topics[CONF_ENTRYTIME_TOPIC] = {
            "topic": self._config[CONF_ENTRYTIME_TOPIC],
            "msg_callback": entrytime_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def exittime_message_received(msg: Any) -> None:
            """Handle exit time message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Unable to parse exit time MQTT message")
                return

            if data.value == 1:
                self._exittime.add(data.index)
            else:
                self._exittime.discard(data.index)

            _LOGGER.debug("Exit Time: %s", self._exittime)
            self.async_write_ha_state()

        topics[CONF_EXITTIME_TOPIC] = {
            "topic": self._config[CONF_EXITTIME_TOPIC],
            "msg_callback": exittime_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def exittime10_message_received(msg: Any) -> None:
            """Handle exit time >10s message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Unable to parse exit time 10 MQTT message")
                return

            if data.value == 1:
                self._exittime10.add(data.index)
            else:
                self._exittime10.discard(data.index)

            _LOGGER.debug("Exit Time >10s: %s", self._exittime10)
            self.async_write_ha_state()

        topics[CONF_EXITTIME10_TOPIC] = {
            "topic": self._config[CONF_EXITTIME10_TOPIC],
            "msg_callback": exittime10_message_received,
            "qos": DEFAULT_QOS,
        }

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass, self._sub_state, topics
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        clear_alarm = self._alarm_state == AlarmControlPanelState.TRIGGERED
        cmd = f"{ALARM_CMD_DISARM}{self._all_cmd_data}"
        _LOGGER.debug("Command disarm: %s", cmd)
        self.publish(self._config[CONF_RAW_TOPIC], cmd)

        if clear_alarm:
            await asyncio.sleep(1)
            cmd = f"{ALARM_CMD_CLEAR}{self._all_cmd_data}"
            _LOGGER.debug("Command clear: %s", cmd)
            self.publish(self._config[CONF_RAW_TOPIC], cmd)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the alarm in home mode."""
        cmd = f"{ALARM_CMD_ARM}{self._home_cmd_data}"
        _LOGGER.debug("Command arm home: %s", cmd)
        self.publish(self._config[CONF_RAW_TOPIC], cmd)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the alarm in away mode."""
        cmd = f"{ALARM_CMD_ARM}{self._away_cmd_data}"
        _LOGGER.debug("Command arm away: %s", cmd)
        self.publish(self._config[CONF_RAW_TOPIC], cmd)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ampio alarm control panels from a config entry."""
    entities_to_create = hass.data[DATA_AMPIO][ALARM_DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioSatelAlarmControlPanel,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
