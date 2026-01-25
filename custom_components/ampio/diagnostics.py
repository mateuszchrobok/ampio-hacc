"""Diagnostics support for Ampio integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DATA_AMPIO, DATA_AMPIO_COORDINATOR

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data.get(DATA_AMPIO, {})
    coordinator = data.get(DATA_AMPIO_COORDINATOR)
    modules = coordinator.data.modules if coordinator else {}

    # Build module info for diagnostics
    module_info: list[dict[str, Any]] = []
    for mac, module in modules.items():
        module_info.append(
            {
                "mac": mac,
                "user_mac": module.user_mac if hasattr(module, "user_mac") else None,
                "name": module.name if hasattr(module, "name") else None,
                "code": module.code if hasattr(module, "code") else None,
                "part_number": module.part_number if hasattr(module, "part_number") else None,
                "software": module.software if hasattr(module, "software") else None,
                "pcb": module.pcb if hasattr(module, "pcb") else None,
                "protocol": module.protocol if hasattr(module, "protocol") else None,
                "configs": {
                    component: len(configs)
                    for component, configs in (
                        module.configs.items() if hasattr(module, "configs") else {}
                    )
                },
            }
        )

    # Get entity counts by platform
    entity_counts: dict[str, int] = {}
    for platform in ["sensor", "binary_sensor", "switch", "light", "cover", "alarm_control_panel"]:
        platform_data = data.get(platform, [])
        if platform_data:
            entity_counts[platform] = len(platform_data)

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "modules": {
            "count": len(module_info),
            "details": module_info,
        },
        "entities": entity_counts,
    }
