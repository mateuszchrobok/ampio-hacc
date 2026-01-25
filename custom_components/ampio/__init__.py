"""Ampio Smart Home System Integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, ServiceCall

from .const import (
    COMPONENTS,
    DATA_AMPIO,
    DATA_AMPIO_COORDINATOR,
    DATA_AMPIO_DISPATCHERS,
    DOMAIN,
)
from .coordinator import AmpioCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_DISPLAY_TEXT = "display_text"
SERVICE_DISPLAY_CLEAR = "display_clear"
SERVICE_DISPLAY_ICON = "display_icon"
SERVICE_BROADCAST_TEMPERATURE = "broadcast_temperature"
SERVICE_SET_FLAG_TIMED = "set_flag_timed"

# Service schemas
SERVICE_DISPLAY_TEXT_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
        vol.Required("text"): cv.string,
        vol.Optional("line", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=4)),
    }
)

SERVICE_DISPLAY_CLEAR_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
    }
)

SERVICE_DISPLAY_ICON_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
        vol.Required("icon"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        vol.Optional("x", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=127)),
        vol.Optional("y", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=63)),
    }
)

SERVICE_BROADCAST_TEMPERATURE_SCHEMA = vol.Schema(
    {
        vol.Required("address"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        vol.Required("temperature"): vol.Coerce(float),
        vol.Optional("type", default="t"): cv.string,
    }
)

SERVICE_SET_FLAG_TIMED_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
        vol.Required("flag"): vol.All(vol.Coerce(int), vol.Range(min=1, max=255)),
        vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        vol.Required("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
    }
)

type AmpioConfigEntry = ConfigEntry[AmpioCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ampio component from YAML (not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AmpioConfigEntry) -> bool:
    """Set up Ampio from a config entry."""
    # Initialize data storage
    hass.data.setdefault(DATA_AMPIO, {})
    for component in COMPONENTS:
        hass.data[DATA_AMPIO].setdefault(component, [])
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS] = []

    # Create and setup coordinator
    coordinator = AmpioCoordinator(hass, entry)
    await coordinator.async_setup()

    # Store coordinator in entry runtime data
    entry.runtime_data = coordinator
    hass.data[DATA_AMPIO][DATA_AMPIO_COORDINATOR] = coordinator

    # Register services
    await async_register_services(hass, coordinator)

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, COMPONENTS)

    # Handle shutdown
    async def async_stop_ampio(_event: Event) -> None:
        """Stop Ampio on Home Assistant shutdown."""
        await coordinator.async_shutdown()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop_ampio))

    return True


async def async_register_services(hass: HomeAssistant, coordinator: AmpioCoordinator) -> None:
    """Register Ampio services."""

    async def handle_display_text(call: ServiceCall) -> None:
        """Handle display_text service call."""
        mac = call.data["mac"].upper().replace(":", "")
        text = call.data["text"]
        line = call.data.get("line", 1)

        # Encode text for LCD display
        # Topic: ampio/to/{mac}/lcd/text/{line}
        topic = f"ampio/to/{mac}/lcd/text/{line}"
        coordinator.publish(topic, text, qos=0, retain=False)

    async def handle_display_clear(call: ServiceCall) -> None:
        """Handle display_clear service call."""
        mac = call.data["mac"].upper().replace(":", "")

        # Topic: ampio/to/{mac}/lcd/clear
        topic = f"ampio/to/{mac}/lcd/clear"
        coordinator.publish(topic, "1", qos=0, retain=False)

    async def handle_display_icon(call: ServiceCall) -> None:
        """Handle display_icon service call."""
        mac = call.data["mac"].upper().replace(":", "")
        icon = call.data["icon"]
        x = call.data.get("x", 0)
        y = call.data.get("y", 0)

        # Topic: ampio/to/{mac}/lcd/icon
        # Payload: icon_id,x,y
        topic = f"ampio/to/{mac}/lcd/icon"
        payload = f"{icon},{x},{y}"
        coordinator.publish(topic, payload, qos=0, retain=False)

    async def handle_broadcast_temperature(call: ServiceCall) -> None:
        """Handle broadcast_temperature service call.

        Broadcasts temperature to the Ampio CAN network.
        Topic: ampio/to/broadcast/{address}/{type}
        """
        address = call.data["address"]
        temperature = call.data["temperature"]
        temp_type = call.data.get("type", "t")

        topic = f"ampio/to/broadcast/{address}/{temp_type}"
        coordinator.publish(topic, f"{temperature:.1f}", qos=0, retain=False)

    async def handle_set_flag_timed(call: ServiceCall) -> None:
        """Handle set_flag_timed service call.

        Sets a flag with automatic timeout using raw CAN command.
        Raw command format: 01 00 [FLAG_MASK x4] [value] [TIME x3]
        """
        mac = call.data["mac"].upper().replace(":", "")
        flag = call.data["flag"]
        value = call.data["value"]
        duration = call.data["duration"]

        # Calculate flag mask (4 bytes, little endian)
        flag_mask = 1 << (flag - 1)
        mask_bytes = flag_mask.to_bytes(4, byteorder="little")

        # Time in seconds as 3 bytes (little endian)
        time_bytes = duration.to_bytes(3, byteorder="little")

        # Build raw command: 01 00 [4 mask bytes] [value] [3 time bytes]
        raw_cmd = bytes([0x01, 0x00]) + mask_bytes + bytes([value]) + time_bytes

        topic = f"ampio/to/{mac}/raw"
        coordinator.publish(topic, raw_cmd.hex(), qos=0, retain=False)

    # Register all services
    if not hass.services.has_service(DOMAIN, SERVICE_DISPLAY_TEXT):
        hass.services.async_register(
            DOMAIN, SERVICE_DISPLAY_TEXT, handle_display_text, schema=SERVICE_DISPLAY_TEXT_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_DISPLAY_CLEAR):
        hass.services.async_register(
            DOMAIN, SERVICE_DISPLAY_CLEAR, handle_display_clear, schema=SERVICE_DISPLAY_CLEAR_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_DISPLAY_ICON):
        hass.services.async_register(
            DOMAIN, SERVICE_DISPLAY_ICON, handle_display_icon, schema=SERVICE_DISPLAY_ICON_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_BROADCAST_TEMPERATURE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_BROADCAST_TEMPERATURE,
            handle_broadcast_temperature,
            schema=SERVICE_BROADCAST_TEMPERATURE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_FLAG_TIMED):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_FLAG_TIMED,
            handle_set_flag_timed,
            schema=SERVICE_SET_FLAG_TIMED_SCHEMA,
        )


async def async_unload_entry(hass: HomeAssistant, entry: AmpioConfigEntry) -> bool:
    """Unload Ampio config entry."""
    # Unsubscribe dispatchers
    dispatchers = hass.data[DATA_AMPIO].get(DATA_AMPIO_DISPATCHERS, [])
    for unsub_dispatcher in dispatchers:
        unsub_dispatcher()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, COMPONENTS)

    # Shutdown coordinator
    if entry.runtime_data:
        await entry.runtime_data.async_shutdown()

    # Clean up data and unregister services
    if unload_ok:
        hass.data[DATA_AMPIO].pop(DATA_AMPIO_COORDINATOR, None)

        # Only unregister services if no other entries are loaded
        remaining_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id
        ]
        if not remaining_entries:
            for service in [
                SERVICE_DISPLAY_TEXT,
                SERVICE_DISPLAY_CLEAR,
                SERVICE_DISPLAY_ICON,
                SERVICE_BROADCAST_TEMPERATURE,
                SERVICE_SET_FLAG_TIMED,
            ]:
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)

    return unload_ok
