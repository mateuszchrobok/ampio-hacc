# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant Custom Component for integrating [Ampio Smart Home System](https://ampio.pl). Communicates via MQTT directly with the Ampio Server's MQTT broker.

**Fork lineage**: kstaniek/ampio-hacc → pszypowicz/ampio-hacc → mateuszchrobok/ampio-hacc

## Development Commands

### Validation
```bash
# Run hassfest validation (same as GitHub Actions)
docker run --rm -v $(pwd):/github/workspace homeassistant/amd64-builder:dev \
  /bin/bash -c "pip install hassfest && hassfest"
```

### Local Testing
```bash
# Copy to HA custom_components (adjust path for your HA instance)
cp -r custom_components/ampio /path/to/ha/config/custom_components/

# Restart Home Assistant to reload
ha core restart  # or restart via UI
```

### Check logs for ampio
```bash
# Filter HA logs for ampio-related messages
grep -i ampio /config/home-assistant.log
```

## Architecture

### Communication Flow
```
Ampio Server MQTT Broker (port 1883)
        ↓
    AmpioAPI (client.py)
        ↓ MQTT messages
    discovery.py
        ↓ creates entities
    Platform files (sensor.py, switch.py, etc.)
        ↓
    Home Assistant Entity Registry
```

### Key Concepts

**Push-based updates**: No polling. MQTT topics publish state changes which entities subscribe to.

**Discovery process** (discovery.py):
1. Subscribe to `ampio/from/info/version` → get server version
2. Publish to `ampio/to/can/dev/list` → request device list
3. For each device MAC, publish to `ampio/to/{mac}/description` → get item names
4. Create entity configs based on module type (models.py)
5. Signal platforms to create entities

**Entity creation pattern**:
- Platforms register via `async_dispatcher_connect(SIGNAL_ADD_ENTITIES, ...)`
- After all modules discovered, `async_load_entities()` fires the signal
- Each platform creates entities from accumulated configs in `hass.data[DATA_AMPIO][component]`

### Data Storage Keys
- `DATA_AMPIO` - Main data dict
- `DATA_AMPIO_API` - AmpioAPI instance
- `DATA_AMPIO_MODULES` - Modules pending discovery (cleared after discovery)
- `DATA_AMPIO_UNIQUE_IDS` - Set of created entity IDs (prevents duplicates)

## Module Type Mappings

All device/entity type mappings are in `models.py`. When adding support for new Ampio modules:

1. Add module type constant to `models.py`
2. Define entity configs in `AmpioModuleInfo.update_configs()`
3. Map MQTT topics to entity attributes
4. Use existing platform (sensor, switch, light, cover, binary_sensor, alarm_control_panel) or create new

## Supported Platforms
- `sensor` - Environmental data (temperature, humidity, IAQ, CO2, pressure)
- `binary_sensor` - Binary inputs
- `switch` - Binary outputs (relays)
- `light` - Dimmers (MDIM-8s), LED (MLED-1), RGBW (MRGBu-1)
- `cover` - Roller shutters (MROL-4s)
- `alarm_control_panel` - Satel integration via MCON

## MQTT Topic Structure

```
ampio/from/{mac}/{item}  - State updates from device
ampio/to/{mac}/{item}    - Commands to device
ampio/from/info/version  - Server version
ampio/from/can/dev/list  - Device discovery response
ampio/from/{mac}/description - Module names/config
```

## Dependencies

- `paho-mqtt>=2.0.0`
- Home Assistant `mqtt` component (for Subscription model)
- Zeroconf discovery: `_ampio-mqtt._tcp.local.`

## GitHub Actions

- **hassfest**: Validates manifest.json and integration structure on every push/PR
