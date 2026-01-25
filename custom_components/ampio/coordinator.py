"""DataUpdateCoordinator for Ampio integration."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_VERSION,
    CONF_BROKER,
    DEFAULT_QOS,
    DOMAIN,
    SIGNAL_ADD_ENTITIES,
    TOPIC_DISCOVERY_REQUEST,
    TOPIC_DISCOVERY_RESPONSE,
    TOPIC_NAMES_REQUEST,
    TOPIC_NAMES_RESPONSE,
    TOPIC_VERSION_REQUEST,
    TOPIC_VERSION_RESPONSE,
)
from .models import AmpioModuleInfo, ItemName, Message, PublishPayloadType

_LOGGER = logging.getLogger(__name__)

# Regex to extract MAC from topic
MAC_FROM_TOPIC_RE = re.compile(r"^ampio/from/(?P<mac>.*)/.*$")


@dataclass
class AmpioData:
    """Class to hold Ampio integration data."""

    modules: dict[str, AmpioModuleInfo] = field(default_factory=dict)
    unique_ids: set[str] = field(default_factory=set)
    entity_configs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    server_version: str | None = None


class AmpioCoordinator(DataUpdateCoordinator[AmpioData]):
    """Coordinator for Ampio MQTT data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # No update interval - data is pushed via MQTT
            update_interval=None,
        )
        self.config_entry = config_entry
        self._mqtt_client: AmpioMQTTClient | None = None
        self._discovery_complete = asyncio.Event()
        self._pending_modules: dict[str, AmpioModuleInfo] = {}
        self.data = AmpioData()

    @property
    def mqtt_client(self) -> AmpioMQTTClient | None:
        """Return the MQTT client."""
        return self._mqtt_client

    async def async_setup(self) -> None:
        """Set up the coordinator - connect to MQTT and start discovery."""
        self._mqtt_client = AmpioMQTTClient(
            self.hass,
            self.config_entry,
            self._handle_message,
        )

        result = await self._mqtt_client.async_connect()
        if result != "OK":
            raise ConfigEntryNotReady(f"Failed to connect to MQTT broker: {result}")

        await self._setup_subscriptions()
        await self._start_discovery()

    async def async_shutdown(self) -> None:
        """Shut down the coordinator."""
        if self._mqtt_client:
            await self._mqtt_client.async_disconnect()

    async def _setup_subscriptions(self) -> None:
        """Set up MQTT topic subscriptions for discovery."""
        if not self._mqtt_client:
            return

        topics = [
            TOPIC_VERSION_RESPONSE,
            TOPIC_DISCOVERY_RESPONSE,
            TOPIC_NAMES_RESPONSE,
        ]
        for topic in topics:
            await self._mqtt_client.async_subscribe(topic, DEFAULT_QOS)

    async def _start_discovery(self) -> None:
        """Start device discovery."""
        if not self._mqtt_client:
            return

        # Request server version and device list
        await self._mqtt_client.async_publish(TOPIC_VERSION_REQUEST, "", 0, False)
        await self._mqtt_client.async_publish(TOPIC_DISCOVERY_REQUEST, "1", 0, False)

    @callback
    def _handle_message(self, msg: Message) -> None:
        """Handle incoming MQTT messages."""
        if msg.topic == TOPIC_VERSION_RESPONSE:
            self._handle_version_info(msg)
        elif msg.topic == TOPIC_DISCOVERY_RESPONSE:
            self._handle_device_list(msg)
        elif msg.subscribed_topic == TOPIC_NAMES_RESPONSE:
            self._handle_module_names(msg)
        else:
            # State update message - dispatch to entities
            self.async_set_updated_data(self.data)

    def _handle_version_info(self, msg: Message) -> None:
        """Process server version info."""
        try:
            data = json.loads(str(msg.payload))
        except (json.JSONDecodeError, ValueError, TypeError) as err:
            _LOGGER.error("Unable to decode Ampio MQTT Server version: %s", err)
            return

        version = data.get(ATTR_VERSION, "N/A")
        self.data.server_version = version

        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            connections={(CONNECTION_NETWORK_MAC, "ampio-mqtt")},
            identifiers={(DOMAIN, "ampio-mqtt")},
            name="Ampio MQTT Server",
            manufacturer="Ampio",
            model="MQTT Server",
            sw_version=version,
        )
        _LOGGER.debug("Ampio MQTT Server version: %s", version)

    def _handle_device_list(self, msg: Message) -> None:
        """Process device list."""
        try:
            payload = json.loads(str(msg.payload))
        except (json.JSONDecodeError, ValueError, TypeError) as err:
            _LOGGER.error("Unable to parse JSON module list: %s", err)
            return

        modules = AmpioModuleInfo.from_topic_payload(payload)

        for module in modules:
            self._pending_modules[module.user_mac] = module
            self._setup_device_registry(module)

            # Request module names
            if self._mqtt_client:
                self.hass.async_create_task(
                    self._mqtt_client.async_publish(
                        TOPIC_NAMES_REQUEST.format(mac=module.user_mac),
                        "1",
                        0,
                        False,
                    )
                )

    def _setup_device_registry(self, module: AmpioModuleInfo) -> None:
        """Register device in device registry."""
        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            **module.as_hass_device(),
        )

    def _handle_module_names(self, msg: Message) -> None:
        """Process module names/descriptions."""
        matched = MAC_FROM_TOPIC_RE.match(msg.topic)
        if not matched:
            return

        mac = matched.group("mac").upper()
        module = self._pending_modules.get(mac)
        if module is None:
            return

        try:
            payload = json.loads(str(msg.payload))
        except (json.JSONDecodeError, ValueError, TypeError) as err:
            _LOGGER.error("Unable to parse JSON module names for %s: %s", mac, err)
            return

        module.names = ItemName.from_topic_payload(payload)
        module.update_configs()

        _LOGGER.info(
            "Discovered: %s-%s (%s): %s",
            module.code,
            module.model,
            module.software,
            module.name,
        )

        # Collect entity configs
        for component, configs in module.configs.items():
            if component not in self.data.entity_configs:
                self.data.entity_configs[component] = []

            for config in configs:
                unique_id = config.get("unique_id")
                if unique_id and unique_id not in self.data.unique_ids:
                    self.data.entity_configs[component].append(config)
                    self.data.unique_ids.add(unique_id)
                else:
                    _LOGGER.debug("Ignoring duplicate: %s", unique_id)

        # Store module data
        self.data.modules[mac] = module
        del self._pending_modules[mac]

        # Check if all modules discovered
        if len(self._pending_modules) == 0:
            _LOGGER.info("All modules discovered")
            self._discovery_complete.set()
            async_dispatcher_send(self.hass, SIGNAL_ADD_ENTITIES)

    def get_entity_configs(self, component: str) -> list[dict[str, Any]]:
        """Get entity configs for a component."""
        return self.data.entity_configs.get(component, [])

    async def async_publish(
        self, topic: str, payload: PublishPayloadType, qos: int = 0, retain: bool = False
    ) -> None:
        """Publish an MQTT message."""
        if self._mqtt_client:
            await self._mqtt_client.async_publish(topic, payload, qos, retain)

    def publish(
        self, topic: str, payload: PublishPayloadType, qos: int = 0, retain: bool = False
    ) -> None:
        """Publish an MQTT message (non-async wrapper)."""
        if self._mqtt_client:
            self.hass.async_create_task(
                self._mqtt_client.async_publish(topic, payload, qos, retain)
            )


class AmpioMQTTClient:
    """Ampio MQTT Client wrapper."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        message_callback: Callable[[Message], None],
    ) -> None:
        """Initialize the MQTT client."""
        self.hass = hass
        self.config_entry = config_entry
        self._message_callback = message_callback
        self._mqttc: mqtt.Client | None = None
        self._paho_lock = asyncio.Lock()
        self._subscriptions: dict[str, int] = {}
        self.connected = False

        self._init_client()

    def _init_client(self) -> None:
        """Initialize the paho MQTT client."""
        import paho.mqtt.client as mqtt

        self._mqttc = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv311,
        )

        data = self.config_entry.data
        username = data.get(CONF_USERNAME)
        password = data.get(CONF_PASSWORD)
        if username:
            self._mqttc.username_pw_set(username, password)

        self._mqttc.on_connect = self._on_connect
        self._mqttc.on_disconnect = self._on_disconnect
        self._mqttc.on_message = self._on_message

    async def async_connect(self) -> str:
        """Connect to the MQTT broker."""
        import paho.mqtt.client as mqtt

        if not self._mqttc:
            return "Client not initialized"

        data = self.config_entry.data
        broker = data[CONF_BROKER]
        port = data.get(CONF_PORT, 1883)
        keepalive = 60

        try:
            result = await self.hass.async_add_executor_job(
                self._mqttc.connect, broker, port, keepalive
            )
        except OSError as err:
            _LOGGER.error("Failed to connect to Ampio MQTT Server: %s", err)
            return str(err)

        if result != 0:
            return mqtt.error_string(result)

        self._mqttc.loop_start()
        return "OK"

    async def async_disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if not self._mqttc:
            return

        def stop() -> None:
            if self._mqttc:
                self._mqttc.loop_stop()

        await self.hass.async_add_executor_job(stop)

    async def async_subscribe(self, topic: str, qos: int = 0) -> None:
        """Subscribe to an MQTT topic."""
        if not self._mqttc:
            return

        self._subscriptions[topic] = qos

        if self.connected:
            async with self._paho_lock:
                await self.hass.async_add_executor_job(self._mqttc.subscribe, topic, qos)

    async def async_publish(
        self, topic: str, payload: PublishPayloadType, qos: int, retain: bool
    ) -> None:
        """Publish an MQTT message."""
        if not self._mqttc:
            return

        async with self._paho_lock:
            _LOGGER.debug("Publishing to %s: %s", topic, payload)
            await self.hass.async_add_executor_job(self._mqttc.publish, topic, payload, qos, retain)

    def _on_connect(
        self,
        _mqttc: mqtt.Client,
        _userdata: Any,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        """Handle MQTT connect."""
        import paho.mqtt.client as mqtt

        if reason_code != mqtt.CONNACK_ACCEPTED:
            _LOGGER.error("Unable to connect to MQTT broker: %s", mqtt.connack_string(reason_code))
            return

        self.connected = True
        _LOGGER.info("Connected to Ampio MQTT broker")

        # Re-subscribe to all topics (use add_job since this is called from paho thread)
        for topic, qos in self._subscriptions.items():
            self.hass.add_job(self.async_subscribe(topic, qos))

    def _on_disconnect(
        self,
        _mqttc: mqtt.Client,
        _userdata: Any,
        _flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        """Handle MQTT disconnect."""
        self.connected = False
        _LOGGER.warning("Disconnected from Ampio MQTT broker: %s", reason_code)

    def _on_message(self, _mqttc: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle incoming MQTT message."""
        from homeassistant.util import dt as dt_util

        _LOGGER.debug(
            "Received message on %s%s: %s",
            msg.topic,
            " (retained)" if msg.retain else "",
            msg.payload,
        )

        # Decode payload
        payload: str | bytes
        try:
            payload = msg.payload.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            payload = msg.payload

        # Find subscribed topic that matches
        subscribed_topic = None
        for topic in self._subscriptions:
            if self._topic_matches(topic, msg.topic):
                subscribed_topic = topic
                break

        message = Message(
            topic=msg.topic,
            payload=payload,
            qos=msg.qos,
            retain=msg.retain,
            subscribed_topic=subscribed_topic,
            timestamp=dt_util.utcnow(),
        )

        self.hass.add_job(self._message_callback, message)

    @staticmethod
    def _topic_matches(subscription: str, topic: str) -> bool:
        """Check if topic matches subscription pattern."""
        from paho.mqtt.matcher import MQTTMatcher

        matcher = MQTTMatcher()
        matcher[subscription] = True
        try:
            next(matcher.iter_match(topic))
            return True
        except StopIteration:
            return False
