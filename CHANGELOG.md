# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.5] - 2025-01-26

### Fixed
- **via_device Warning**: Create MQTT Server device before module devices to prevent warning about via_device referencing non-existent device
- **Unknown Module Types**: Added support for module types 24 (RUPS - Relay Unit Power Sockets) and 69 (MKIN-MULTI - Multi-function module)
- **Linting**: Replaced deprecated `asyncio.TimeoutError` with builtin `TimeoutError`

### Added
- `RUPSModuleInfo` class for type 24 modules (230V power socket relay units)
- `MKINMULTIModuleInfo` class for type 69 modules (Kinetic/Chorus/IAQ/Rekuperator)

## [1.4.4] - 2025-01-26

### Fixed
- **Device Discovery Schema**: Support both old `{"s":..., "d":[...]}` and new `{"devices":[...]}` JSON formats from MQTT broker
  - Updated `AMPIO_DEVICES_SCHEMA` in validators.py to accept both `"d"` and `"devices"` keys
  - Updated `from_topic_payload()` in models.py to check for both keys

## [1.4.3] - 2025-01-26

### Fixed
- **CI/CD Linting Errors**: Fixed ruff and mypy errors
  - Removed duplicate `Callable` import in client.py
  - Fixed import sorting in alarm_control_panel.py
  - Added noqa comment for intentional TypeAlias usage (Python 3.11 compat)

## [1.4.2] - 2025-01-26

### Fixed
- **Python 3.11 Compatibility**: Changed `type X = Y` syntax to `TypeAlias` for Python 3.11 support
- **Internal HA Import Dependency**: Replaced `homeassistant.components.mqtt.Subscription` import with local dataclass to avoid breaking on HA internal changes

## [1.4.1] - 2025-01-26

### Fixed
- **OptionsFlow config_entry Error**: Fixed `AttributeError: property 'config_entry' of 'AmpioOptionsFlow' object has no setter` in Home Assistant 2024.1+
- **Alarm State Constants**: Fixed `ImportError: cannot import name 'STATE_ALARM_ARMED_AWAY'` by migrating to `AlarmControlPanelState` enum

## [1.4.0] - 2025-01-25

### Added
- **New Module Support**:
  - MCON-DL-s (code 30): DALI lighting control module
  - MCON-IR (code 31): Infrared control module
  - MCON-HVAC-p (code 32): HVAC integration module
  - MOUT-4s (code 51): 4-channel analog output module (DIN rail)
  - MOUT-4p (code 52): 4-channel analog output module (flush-mount)
  - MAV-AMP-s (code 54): Audio amplifier module
  - MRDN-5s (code 55): 5-channel dimmer module
- **METEO-1s Weather Station Enhancements**:
  - Wind speed sensor (m/s)
  - Wind direction sensor (degrees)
  - Precipitation/rain sensor (mm)
  - UV index sensor
- **Wireless Module Battery Monitoring**:
  - Battery level sensors for all wireless modules (WL-REL-2p, WL-REL-ROL1p, WL-OC-RGBW1p, WZ-SENS-TMP-p)
  - New AmpioBatterySensorConfig class
- **New Sensor Configuration Classes**:
  - AmpioAnalogOutputSensorConfig for analog output monitoring
  - AmpioAudioSensorConfig for audio amplifier volume/source
  - AmpioWindSpeedSensorConfig, AmpioWindDirectionSensorConfig
  - AmpioPrecipitationSensorConfig, AmpioUVIndexSensorConfig

### Changed
- Wireless modules now inherit from WLSensorModuleInfo for automatic battery monitoring
- All 52 TYPE_CODES entries now have corresponding CLASS_FACTORY handlers

### Documentation
- Added comprehensive user documentation (docs/ENTITIES.md, docs/SERVICES.md)
- Added troubleshooting guide (docs/TROUBLESHOOTING.md)
- Added FAQ (docs/FAQ.md)
- Added developer documentation (docs/API_REFERENCE.md, docs/PLATFORM_GUIDE.md, docs/TESTING.md)

## [1.3.0] - 2025-01-25

### Added
- CHANGELOG.md for tracking version history
- CONTRIBUTING.md with contribution guidelines
- docs/ARCHITECTURE.md with component architecture documentation
- docs/MQTT_PROTOCOL.md with MQTT topic and payload documentation
- Constants for magic numbers (switch, cover, alarm commands, PCB versions)
- Proper type hints for paho-mqtt callbacks
- State message parsing mixins for code deduplication
- Comprehensive test infrastructure with MQTT fixtures
- Platform tests for sensor, switch, light, cover, binary_sensor
- Coordinator tests for discovery flow

### Changed
- Replaced magic numbers with named constants throughout codebase
- Improved error handling with proper logging levels
- Fixed silent RGB parsing failure in light.py
- Standardized JSON error handling with JSONDecodeError

### Fixed
- Silent failures in MQTT message parsing now log warnings
- Type safety improvements in callback signatures

## [1.2.0] - 2024-01-15

### Added
- Home Assistant 2024.1+ compatibility
- Climate platform support for MRT-16s modules
- Event platform support for touch panel button events
- Diagnostics platform for debugging
- Generic module handler for unknown module types
- Support for additional module types (M-IN, M-REL, M-OC series)
- Wireless module support (WL-REL, WL-OC-RGBW)

### Changed
- Migrated to paho-mqtt 2.0.0 API
- Updated coordinator pattern for MQTT handling
- Improved entity registration with has_entity_name

### Fixed
- Python 3.12 compatibility issues
- Type errors resolved with mypy

## [1.1.0] - 2023-06-01

### Added
- HACS compatibility
- Config flow for UI-based setup
- Zeroconf discovery support

### Changed
- Restructured as Home Assistant custom component

## [1.0.0] - 2023-01-01

### Added
- Initial release
- Support for M-SENS environmental sensors
- Support for M-DOT touch panels
- Support for M-DIM dimmers
- Support for M-ROL roller shutters
- Support for M-PR relay modules
- Support for M-CON Satel alarm integration
- MQTT-based communication with Ampio Server
