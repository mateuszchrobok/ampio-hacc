"""DataUpdateCoordinator for Ampio integration."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import groupby
from operator import attrgetter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_VERSION,
    CONF_BROKER,
    DATA_AMPIO,
    DATA_AMPIO_API,
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
from .project_db import (
    PROJECT_TABLES,
    TABLE_DEVICES,
    TABLE_OBJECTS,
    TOPIC_PROJECT_REQUEST,
    TOPIC_PROJECT_RESPONSE,
    parse_project_db,
)

# Type for message callbacks
MessageCallbackType = Callable[[Any], None]

_LOGGER = logging.getLogger(__name__)

# Regex to extract MAC from topic
MAC_FROM_TOPIC_RE = re.compile(r"^ampio/from/(?P<mac>.*)/.*$")

# How long to wait for the project database before giving up on item names. The
# server serves the whole ``objects`` table in one ~1.3 MB message, so this covers
# a slow first publish rather than a round trip.
DISCOVERY_TIMEOUT = 45


@dataclass(frozen=True)
class Subscription:
    """Entity subscription data class."""

    topic: str
    is_active: Callable[[], bool]
    job: MessageCallbackType
    qos: int
    encoding: str | None


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
        self._project_tables: dict[str, dict[str, Any]] = {}
        self.data = AmpioData()

    @property
    def _project_user(self) -> str:
        """Return the MQTT user whose project namespace we read names from."""
        return str(self.config_entry.data.get(CONF_USERNAME) or "admin")

    @property
    def _project_topics(self) -> dict[str, str]:
        """Map each project response topic to the table it carries."""
        user = self._project_user
        return {
            TOPIC_PROJECT_RESPONSE.format(user=user, table=table): table for table in PROJECT_TABLES
        }

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

        # Create MQTT Server device FIRST (before any module devices)
        # This prevents via_device warnings when module devices reference it
        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            connections={(CONNECTION_NETWORK_MAC, "ampio-mqtt")},
            identifiers={(DOMAIN, "ampio-mqtt")},
            name="Ampio MQTT Server",
            manufacturer="Ampio",
            model="MQTT Server",
        )

        # Store MQTT client at DATA_AMPIO_API for entity subscriptions
        self.hass.data[DATA_AMPIO][DATA_AMPIO_API] = self._mqtt_client

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
        topics.extend(
            TOPIC_PROJECT_RESPONSE.format(user=self._project_user, table=table)
            for table in PROJECT_TABLES
        )
        for topic in topics:
            await self._mqtt_client.async_subscribe(topic, qos=DEFAULT_QOS)

    async def _start_discovery(self) -> None:
        """Start device discovery."""
        if not self._mqtt_client:
            return

        # Request server version and device list
        await self._mqtt_client.async_publish(TOPIC_VERSION_REQUEST, "", 0, False)
        await self._mqtt_client.async_publish(TOPIC_DISCOVERY_REQUEST, "1", 0, False)

        # Request the project tables that carry the item names. Each table is
        # requested by publishing its own name as the payload.
        project_request = TOPIC_PROJECT_REQUEST.format(user=self._project_user)
        for table in PROJECT_TABLES:
            await self._mqtt_client.async_publish(project_request, table, 0, False)

        # Start a timeout task to complete discovery if descriptions don't arrive
        self.hass.async_create_task(self._discovery_timeout())

    async def _discovery_timeout(self) -> None:
        """Complete discovery if the project database never arrives."""
        await asyncio.sleep(DISCOVERY_TIMEOUT)
        if self._pending_modules:
            _LOGGER.warning(
                "Project database timeout: %d modules still pending, completing "
                "discovery without item names",
                len(self._pending_modules),
            )
            self._complete_discovery("timeout")

    def _complete_discovery(self, reason: str) -> None:
        """Build the entity configs of every pending module and publish them."""
        for mac, module in list(self._pending_modules.items()):
            module.update_configs()
            _LOGGER.info(
                "Discovered (%s): %s-%s (%s): %s",
                reason,
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
            # Store module data
            self.data.modules[mac] = module

        self._pending_modules.clear()
        _LOGGER.info("All modules discovered (via %s)", reason)
        self._discovery_complete.set()

        # Copy entity configs to hass.data for platform discovery
        from .const import DATA_AMPIO

        for component, configs in self.data.entity_configs.items():
            if component not in self.hass.data[DATA_AMPIO]:
                self.hass.data[DATA_AMPIO][component] = []
            self.hass.data[DATA_AMPIO][component].extend(configs)
            _LOGGER.info("Added %d %s entities for discovery", len(configs), component)

        async_dispatcher_send(self.hass, SIGNAL_ADD_ENTITIES)

    @callback
    def _handle_message(self, msg: Message) -> None:
        """Handle incoming MQTT messages."""
        if msg.topic == TOPIC_VERSION_RESPONSE:
            self._handle_version_info(msg)
        elif msg.topic == TOPIC_DISCOVERY_RESPONSE:
            self._handle_device_list(msg)
        elif msg.topic in self._project_topics:
            self._handle_project_table(self._project_topics[msg.topic], msg)
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

        # Update existing device with version info (device created in async_setup)
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "ampio-mqtt")})
        if device:
            device_registry.async_update_device(device.id, sw_version=version)
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

            # Copy entity configs to hass.data for platform discovery
            from .const import DATA_AMPIO

            for component, configs in self.data.entity_configs.items():
                if component not in self.hass.data[DATA_AMPIO]:
                    self.hass.data[DATA_AMPIO][component] = []
                self.hass.data[DATA_AMPIO][component].extend(configs)
                _LOGGER.info("Added %d %s entities for discovery", len(configs), component)

            async_dispatcher_send(self.hass, SIGNAL_ADD_ENTITIES)

    def _handle_project_table(self, table: str, msg: Message) -> None:
        """Store one project table, and apply the names once both have arrived."""
        try:
            payload = json.loads(str(msg.payload))
        except (json.JSONDecodeError, ValueError, TypeError) as err:
            _LOGGER.error("Unable to parse project table %s: %s", table, err)
            return

        self._project_tables[table] = payload
        if any(name not in self._project_tables for name in PROJECT_TABLES):
            return
        if not self._pending_modules:
            return

        try:
            names = parse_project_db(
                self._project_tables[TABLE_DEVICES],
                self._project_tables[TABLE_OBJECTS],
            )
        except Exception:  # pylint: disable=broad-except
            # A malformed table must leave discovery to the timeout path rather
            # than taking the whole integration down.
            _LOGGER.exception("Unable to build item names from the project database")
            return

        named = 0
        for module in self._pending_modules.values():
            # The device list reports the MSERV as user_mac "1" while the project
            # stores every MAC as a 16-bit number, so compare zero-padded.
            module_names = names.get(module.user_mac.zfill(4))
            if module_names:
                module.names = module_names
                named += 1

        _LOGGER.info(
            "Project database applied: %d of %d modules named",
            named,
            len(self._pending_modules),
        )
        self._complete_discovery("project database")

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
    """Ampio MQTT Client wrapper with entity subscription support."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        message_callback: Callable[[Message], None],
    ) -> None:
        """Initialize the MQTT client."""
        self.hass = hass
        self.config_entry = config_entry
        self._coordinator_callback = message_callback
        self._mqttc: mqtt.Client | None = None
        self._paho_lock = asyncio.Lock()
        # Internal subscriptions for discovery (topic -> qos)
        self._discovery_subscriptions: dict[str, int] = {}
        # Entity subscriptions (list of Subscription objects)
        self.subscriptions: list[Subscription] = []
        self.connected = False
        self._connected_event = asyncio.Event()

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

        # Wait for connection to be fully established (on_connect callback)
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=10.0)
        except TimeoutError:
            _LOGGER.error("Timeout waiting for MQTT connection")
            return "Connection timeout"

        return "OK"

    async def async_disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if not self._mqttc:
            return

        def stop() -> None:
            if self._mqttc:
                self._mqttc.loop_stop()

        await self.hass.async_add_executor_job(stop)

    async def async_subscribe(
        self,
        topic: str,
        msg_callback: MessageCallbackType | None = None,
        qos: int = 0,
        encoding: str | None = "utf-8",
    ) -> Callable[[], None] | None:
        """Subscribe to an MQTT topic.

        If msg_callback is provided, this is an entity subscription that returns
        an unsubscribe callable. Otherwise, it's a discovery subscription.
        """
        if not self._mqttc:
            return None

        if msg_callback is None:
            # Simple discovery subscription
            self._discovery_subscriptions[topic] = qos
            if self.connected:
                async with self._paho_lock:
                    await self.hass.async_add_executor_job(self._mqttc.subscribe, topic, qos)
            return None

        # Entity subscription with callback
        if not isinstance(topic, str):
            raise HomeAssistantError("Topic needs to be a string!")

        subscription = Subscription(topic, lambda: True, msg_callback, qos, encoding)
        self.subscriptions.append(subscription)

        # Perform actual subscription if connected
        if self.connected:
            await self._async_perform_subscription(topic, qos)

        @callback
        def async_remove() -> None:
            """Remove subscription."""
            if subscription not in self.subscriptions:
                raise HomeAssistantError("Can't remove subscription twice")
            self.subscriptions.remove(subscription)

            if any(other.topic == topic for other in self.subscriptions):
                # Other subscriptions on topic remaining - don't unsubscribe
                return

            # Only unsubscribe if connected
            if self.connected:
                self.hass.async_create_task(self._async_unsubscribe(topic))

        return async_remove

    async def _async_perform_subscription(self, topic: str, qos: int) -> None:
        """Perform a paho-mqtt subscription."""
        if not self._mqttc:
            return

        _LOGGER.debug("Subscribing entity to %s", topic)
        async with self._paho_lock:
            result, _ = await self.hass.async_add_executor_job(self._mqttc.subscribe, topic, qos)
            if result != 0:
                _LOGGER.error("Failed to subscribe to %s: result=%s", topic, result)

    async def _async_unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic."""
        if not self._mqttc:
            return

        _LOGGER.debug("Unsubscribing from %s", topic)
        async with self._paho_lock:
            await self.hass.async_add_executor_job(self._mqttc.unsubscribe, topic)

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

        # Signal that connection is ready
        self.hass.loop.call_soon_threadsafe(self._connected_event.set)

        # Re-subscribe to discovery topics
        for topic, qos in self._discovery_subscriptions.items():
            self.hass.add_job(self._async_perform_subscription, topic, qos)

        # Re-subscribe to entity topics (group by topic to use highest qos)
        keyfunc = attrgetter("topic")
        for topic, subs in groupby(sorted(self.subscriptions, key=keyfunc), keyfunc):
            max_qos = max(subscription.qos for subscription in subs)
            self.hass.add_job(self._async_perform_subscription, topic, max_qos)

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
        _LOGGER.debug(
            "Received message on %s%s: %s",
            msg.topic,
            " (retained)" if msg.retain else "",
            msg.payload,
        )

        timestamp = dt_util.utcnow()

        # Decode payload for discovery subscriptions
        payload: str | bytes
        try:
            payload = msg.payload.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            payload = msg.payload

        # Check if this is a discovery topic message
        subscribed_topic = None
        for topic in self._discovery_subscriptions:
            if self._topic_matches(topic, msg.topic):
                subscribed_topic = topic
                break

        if subscribed_topic:
            # Send to coordinator callback for discovery messages
            message = Message(
                topic=msg.topic,
                payload=payload,
                qos=msg.qos,
                retain=msg.retain,
                subscribed_topic=subscribed_topic,
                timestamp=timestamp,
            )
            self.hass.add_job(self._coordinator_callback, message)

        # Dispatch to entity subscriptions
        for subscription in self.subscriptions:
            if not self._topic_matches(subscription.topic, msg.topic):
                continue

            # Decode payload with subscription's encoding
            sub_payload: str | bytes = msg.payload
            if subscription.encoding is not None:
                try:
                    sub_payload = msg.payload.decode(subscription.encoding)
                except (AttributeError, UnicodeDecodeError):
                    _LOGGER.warning(
                        "Can't decode payload %s on %s with encoding %s",
                        msg.payload,
                        msg.topic,
                        subscription.encoding,
                    )
                    continue

            entity_message = Message(
                topic=msg.topic,
                payload=sub_payload,
                qos=msg.qos,
                retain=msg.retain,
                subscribed_topic=subscription.topic,
                timestamp=timestamp,
            )
            # Use add_job since we're in the paho thread (thread-safe)
            self.hass.add_job(subscription.job, entity_message)

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
