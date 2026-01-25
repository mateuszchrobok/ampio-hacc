# Home Assistant Ampio Custom Integration

[![CI](https://github.com/mateuszchrobok/ampio-hacc/actions/workflows/ci.yaml/badge.svg)](https://github.com/mateuszchrobok/ampio-hacc/actions/workflows/ci.yaml)
[![GH-release](https://img.shields.io/github/v/release/mateuszchrobok/ampio-hacc.svg?style=flat-square)](https://github.com/mateuszchrobok/ampio-hacc/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/mateuszchrobok/ampio-hacc.svg?style=flat-square)](https://github.com/mateuszchrobok/ampio-hacc/commits/update_hacs)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs)

[![Ampio](https://ampio.pl/wp-content/themes/1140FluidStarkers/images/ampio_dark.png)](https://ampio.pl)

Custom integration for [Ampio Smart Home System](https://ampio.pl) with Home Assistant.

Connects via MQTT directly to the broker running on Ampio Server.

## Supported Modules

| Module | Description |
|--------|-------------|
| MSERV-3s | Server flags |
| MCON | Satel integration |
| MSENS | Environmental sensors (both types) |
| MROL-4s | Roller shutters |
| MPR-8s | Relay outputs |
| MOC-4 | Output controller |
| MRT-16s | Temperature sensors |
| MLED-1 | LED controller |
| MDIM-8s | Dimmers |
| MRGBu-1 | RGBW controller |
| MDOT-2/4/9/15LCD | Touch panels |

**Required**: Ampio MQTT Bridge version 3.41.2+

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu → Custom repositories
4. Add `https://github.com/mateuszchrobok/ampio-hacc` as Integration
5. Search for "Ampio" and install
6. Restart Home Assistant

### Manual

Copy the `custom_components/ampio` folder to your Home Assistant's `custom_components` directory.

## Configuration

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for **Ampio**
4. Enter the Ampio Server IP address (default port: 1883)
5. Use admin credentials from Ampio Smart Home Application
6. Click **Submit**

> **Note**: This custom integration uses the same domain as Home Assistant's built-in Ampio integration. The custom component provides enhanced functionality and will take precedence when installed.

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run linting
ruff check custom_components/ampio

# Run tests
pytest tests/ -v
```

## Credits & Attribution

This project is a fork of the original Ampio Home Assistant integration.

### Original Authors
- **Klaudiusz Staniek** ([@kstaniek](https://github.com/kstaniek)) - Original creator
  - Repository: https://github.com/kstaniek/ampio-hacc

### Contributors
- **Przemysław Szypowicz** ([@pszypowicz](https://github.com/pszypowicz)) - Hassfest fixes
  - Fork: https://github.com/pszypowicz/ampio-hacc

### Current Maintainer
- **Mateusz Chrobok** ([@mateuszchrobok](https://github.com/mateuszchrobok))

## Thanks

Special thanks to Olek from Ampio for help building the stable MQTT Broker.

## License

MIT License - see [LICENSE](LICENSE) for details.
Original copyright © 2020 Klaudiusz Staniek.
