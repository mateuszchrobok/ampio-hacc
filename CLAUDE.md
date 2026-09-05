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

**Discovery process** (coordinator.py):
1. Subscribe to `ampio/from/info/version` → get server version
2. Publish to `ampio/to/can/dev/list` → request device list
3. Publish `devices`, then `objects`, as the payload of `ampio/control/{user}/config` →
   read the project tables back on `ampio/fromDB/{user}/config/{table}` and rebuild the item
   names from them (project_db.py)
4. Create entity configs based on module type (models.py)
5. Signal platforms to create entities

**Item names do NOT come from the modules.** The legacy step — publish to
`ampio/to/{mac}/description`, read `ampio/from/{mac}/description` — is **not answered by Ampio
MQTT bridge 5.x**. Every module times out, `AmpioModuleInfo.names` stays empty, and every
name-driven platform silently produces zero entities while the state topics stay live and
retained. `ampio/to/info/version` is dead the same way; only `ampio/to/can/dev/list` still
answers, which is why devices appear but their items do not.

The names live in the server's project database instead:
- `devices` — `id`, `mac` (the user MAC as an integer: 34266 → `85DA`), `typ_urzadzenia`
- `objects` — `id_urzadzenia`, `typ_komponentu`, `funkcja` (**the 1-based index used in the
  state topic**), `opis_menu` (the human name)

`names` is keyed by that 1-based index — the same base every builder in models.py assumes.
Rows are applied in `id` order and the first to claim an index wins, because the project also
holds group objects ("Cały dom") that reuse a physical item's index.

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
- `binary_sensor` - Binary inputs, and Satel alarm zones (`bi`) behind an M-CON
- `switch` - Binary outputs (relays)
- `number` - 8-bit analog flags (`afu8`), writable 0-255
- `light` - Dimmers (MDIM-8s), LED (MLED-1), RGBW (MRGBu-1)
- `cover` - Roller shutters (MROL-4s)
- `alarm_control_panel` - Satel integration via MCON

**8-bit flags write as raw CAN, not to a `/cmd` topic.** There is no
`ampio/to/{mac}/afu8/{n}/cmd`. The frame is `7AF9` + value byte + **0-based**
index byte, ASCII hex, on `ampio/to/{mac}/raw` — value first, index second. The
reference is Ampio's own `node-red-contrib-ampio` (`ampioin/out.js`), whose
`afu8` branch is the only independent implementation of this write; every other
writable type there falls through to the `/cmd` form. The encoder is
`models.analog_flag_raw_payload`, verified byte-for-byte against that node's
output for all 65536 (value, index) pairs — but **never yet confirmed against
hardware**, and no `ampio/to` command of any kind has been captured on the
reference installation.

**A project row is not evidence that anything exists.** Ampio Designer
pre-allocates blocks of `objects` rows and leaves them nameless; `satel_wej` is
the extreme case, at 2403 rows on the reference installation against ~48 live
`bi` topics, 2062 of them on an M-CON that bridges a heat pump and has no alarm
panel. `PLACEHOLDER_NAMES` in `project_db.py` is therefore a correctness filter,
not a cosmetic one — it is what turns those 2403 rows into 15 entities. The
second guard is firmware: only `soft_ver % 100 == 1` (INTEGRA) M-CONs publish
`state/bi/<n>` at all, which is what `MCONModuleInfo` checks.

**A Satel zone has no device class.** Nothing on the wire or in the project says
whether zone *n* is a PIR, a door reed or a tamper loop. Names like "PIR Salon"
are one installer's convention. The `M:`/`D:`/`W:` name-prefix mechanism is the
only declaration the integration honours.

## MQTT Topic Structure

```
ampio/from/{mac}/{item}  - State updates from device
ampio/to/{mac}/{item}    - Commands to device
ampio/from/info/version  - Server version
ampio/from/can/dev/list  - Device discovery response
ampio/from/{mac}/description - Module names/config (DEAD on bridge 5.x — never answered)

ampio/control/{user}/config          - Request a project table; payload IS the table name
ampio/fromDB/{user}/config/{table}   - The table, e.g. devices / objects / groups / scenes
device_api/to/version                - Server version (replaces the dead ampio/to/info/version)
device_api/to/{mac_hex_lower}/get_data - Module info; answers on device_api/from/{MAC}/info
```

## Dependencies

- `paho-mqtt>=2.0.0`
- Home Assistant `mqtt` component (for Subscription model)
- Zeroconf discovery: `_ampio-mqtt._tcp.local.`

## GitHub Actions

- **hassfest**: Validates manifest.json and integration structure on every push/PR
