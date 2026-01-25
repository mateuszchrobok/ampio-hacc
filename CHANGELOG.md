# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
