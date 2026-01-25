# CLAUDE.md - Ampio Home Assistant Custom Component

## Project Overview

This is a **Home Assistant Custom Component** for integrating [Ampio Smart Home System](https://ampio.pl) with Home Assistant. It communicates via MQTT directly with the Ampio Server's MQTT broker.

### Fork History
- **Original**: [kstaniek/ampio-hacc](https://github.com/kstaniek/ampio-hacc) by Klaudiusz Staniek (2020)
- **Intermediate**: [pszypowicz/ampio-hacc](https://github.com/pszypowicz/ampio-hacc) by Przemysław Szypowicz (hassfest fixes)
- **This Fork**: [mateuszchrobok/ampio-hacc](https://github.com/mateuszchrobok/ampio-hacc)

## Technical Architecture

### Communication
- **Protocol**: MQTT (push-based, no polling)
- **Discovery**: Zeroconf (`_ampio-mqtt._tcp.local.`)
- **Required**: Ampio MQTT Bridge version 3.41.2+

### Supported Hardware (14 modules)
| Module | Description |
|--------|-------------|
| MSERV-3s | Server flags |
| MCON | Satel alarm integration |
| MSENS | Environmental sensors (both types) |
| MROL-4s | Roller shutters |
| MPR-8s | Relay outputs |
| MOC-4 | Output controller |
| MRT-16s | Temperature sensors |
| MLED-1 | LED controller |
| MDIM-8s | Dimmer |
| MRGBu-1 | RGBW LED |
| MDOT-2/4/9/15LCD | Touch panels |

### HA Platforms
- `switch` - Binary outputs
- `binary_sensor` - Binary inputs
- `sensor` - Environmental data (temperature, humidity, IAQ, CO2, etc.)
- `light` - Dimmers, LED, RGBW
- `cover` - Roller shutters
- `alarm_control_panel` - Satel integration

## Project Structure

```
ampio-hacc/
├── custom_components/ampio/
│   ├── __init__.py          # Integration setup, config entry
│   ├── manifest.json        # HA integration manifest
│   ├── config_flow.py       # UI configuration flow
│   ├── const.py             # Constants and defaults
│   ├── client.py            # MQTT client wrapper
│   ├── discovery.py         # Device/entity discovery
│   ├── entity.py            # Base entity classes
│   ├── models.py            # Data models, type mappings (largest file)
│   ├── subscription.py      # MQTT subscription management
│   ├── validators.py        # Input validation
│   ├── data_entry.py        # Config data handling
│   ├── debug_info.py        # Debug utilities
│   ├── sensor.py            # Sensor platform
│   ├── binary_sensor.py     # Binary sensor platform
│   ├── switch.py            # Switch platform
│   ├── light.py             # Light platform (dimmer, RGBW)
│   ├── cover.py             # Cover platform (shutters)
│   ├── alarm_control_panel.py # Satel alarm platform
│   ├── strings.json         # UI strings
│   └── translations/        # Localization
├── hacs.json                # HACS configuration
├── info.md                  # HACS info page
└── static/                  # Documentation images
```

## Key Files

### models.py (~1,012 lines)
Contains all data models, device type mappings, and device classes. This is the largest file and defines:
- 44 device class mappings
- Module type definitions
- Entity attribute mappings

### client.py
MQTT client implementation with:
- Connection management
- Message handling
- Reconnection logic

### discovery.py
Handles automatic discovery of Ampio devices via:
- MQTT topic parsing
- Entity creation based on module type

## Configuration

### Via Home Assistant UI
1. Settings → Integrations → Add → Ampio
2. Enter Ampio Server IP (default port: 1883)
3. Username: `admin`, Password: Ampio admin password

### Required Ampio Setup
- MQTT Bridge enabled on Ampio Server
- Minimum bridge version: 3.41.2

## Development Notes

### Code Quality
- Modern async/await patterns throughout
- Clean separation of concerns
- Push-based updates (efficient)
- Proper HA device registry integration

### Known Limitations
- `paho-mqtt==1.5.0` pinned (current is 2.x)
- Single MQTT client connection at a time
- Some debug logging is sparse

### Testing Changes
1. Copy `custom_components/ampio/` to HA config
2. Restart Home Assistant
3. Check logs: `docker logs ix-home-assistant-home-assistant-1 | grep ampio`

## Local Development

### Installation for Testing
```bash
# Copy to HA custom_components
scp -r custom_components/ampio root@10.10.10.10:/mnt/pool/docker/home-assistant/config/custom_components/

# Or via docker exec
ssh root@10.10.10.10 "docker exec ix-home-assistant-home-assistant-1 ls /config/custom_components/"
```

### Checking Logs
```bash
ssh root@10.10.10.10 "docker logs ix-home-assistant-home-assistant-1 2>&1 | grep -i ampio"
```

### Restart Integration
```bash
# Full HA restart
ssh root@10.10.10.10 "docker restart ix-home-assistant-home-assistant-1"

# Or reload integration via HA UI
```

## Use Case: IAQ Ventilation

This fork is primarily used for reading MSENS IAQ (Indoor Air Quality) sensors to automate ventilation. Key sensors:
- `sensor.msens_sypialnia_iaq` - Master bedroom IAQ
- `sensor.msens_sypialnia_dzieci_iaq` - Children's bedroom IAQ

IAQ values:
- 0-50: Excellent
- 51-100: Good
- 101-150: Moderate
- 151-200: Poor
- 201+: Very poor

## Related Documentation

- **Parent CLAUDE.md**: `/Users/M/work/homeassistant/CLAUDE.md` - Full HA setup context
- **Ampio Website**: https://ampio.pl
- **Original Repo**: https://github.com/kstaniek/ampio-hacc

## License

MIT License - Original copyright © 2020 Klaudiusz Staniek
