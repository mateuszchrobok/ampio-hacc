# Ampio-HACC Architecture

This document describes the architecture and design of the Ampio Home Assistant Custom Component.

## Overview

The Ampio integration communicates with Ampio Smart Home systems via MQTT. The Ampio Server acts as an MQTT broker and gateway to the CAN bus network connecting all Ampio modules.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Home Assistant                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Ampio Integration                       │  │
│  │                                                            │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐  │  │
│  │  │ Config Flow  │───▶│ Coordinator  │───▶│  Platforms  │  │  │
│  │  └──────────────┘    └──────┬───────┘    └─────────────┘  │  │
│  │                             │                              │  │
│  │                             ▼                              │  │
│  │                    ┌──────────────┐                        │  │
│  │                    │ MQTT Client  │                        │  │
│  │                    └──────┬───────┘                        │  │
│  └───────────────────────────┼───────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────┘
                               │ MQTT
                               ▼
                    ┌──────────────────┐
                    │  Ampio Server    │
                    │  (MQTT Broker)   │
                    └────────┬─────────┘
                             │ CAN Bus
                             ▼
              ┌──────────────────────────────┐
              │       Ampio Modules          │
              │ M-SENS, M-DOT, M-DIM, M-ROL  │
              └──────────────────────────────┘
```

## Key Components

### Config Flow (`config_flow.py`)

Handles UI-based configuration:
- Zeroconf discovery of Ampio Server
- Manual configuration entry
- Connection validation

### Coordinator (`coordinator.py`)

Central orchestrator for the integration:
- Manages MQTT connection lifecycle
- Handles device discovery
- Coordinates entity updates
- Maintains module registry

Discovery sequence:
1. Connect to MQTT broker
2. Subscribe to discovery topics
3. Request server version
4. Request device list
5. For each device, request description
6. Create entity configurations
7. Signal platforms to create entities

### MQTT Client (`client.py`)

Low-level MQTT communication:
- paho-mqtt wrapper with async support
- Topic subscription management
- Message publishing
- Connection state tracking

### Models (`models.py`)

Data models and entity configuration:
- `AmpioModuleInfo` - Base class for module metadata
- Module-specific classes (e.g., `MSENSModuleInfo`, `MCONModuleInfo`)
- Entity configuration classes for each platform
- MQTT message data classes

### Entity Base (`entity.py`)

Base class for all Ampio entities:
- Common entity attributes
- MQTT subscription management
- Coordinator integration
- Device info generation

### Platforms

Each platform handles specific entity types:

| Platform | Entity Types | Modules |
|----------|--------------|---------|
| `sensor` | Temperature, humidity, pressure, IAQ | M-SENS, METEO |
| `binary_sensor` | Motion, door, window, touch | M-DOT, M-PR, M-IN |
| `switch` | Relays, flags | M-PR, M-REL, M-SERV |
| `light` | Dimmers, RGB, RGBW | M-DIM, M-LED, M-RGB |
| `cover` | Roller shutters | M-ROL |
| `climate` | Thermostats | M-RT |
| `alarm_control_panel` | Satel integration | M-CON |
| `event` | Button press events | M-DOT |

## Data Flow

### Discovery Flow

```
1. Integration Setup
   └── async_setup_entry()
       └── AmpioCoordinator.async_setup()
           └── AmpioMQTTClient.async_connect()

2. Discovery
   ├── Subscribe to: ampio/from/info/version
   ├── Subscribe to: ampio/from/can/dev/list
   ├── Subscribe to: ampio/from/+/description
   │
   ├── Publish to: ampio/to/info/version
   └── Publish to: ampio/to/can/dev/list

3. Module Processing
   └── For each module in device list:
       ├── Create AmpioModuleInfo
       ├── Register device
       ├── Request description (ampio/to/{mac}/description)
       └── On description received:
           ├── Parse item names
           ├── Generate entity configs
           └── Store in coordinator.data

4. Entity Creation
   └── When all modules discovered:
       └── async_dispatcher_send(SIGNAL_ADD_ENTITIES)
           └── Each platform creates entities from configs
```

### State Update Flow

```
MQTT Message Received
    │
    ▼
AmpioMQTTClient._on_message()
    │
    ▼
Entity.subscribe_topics() callback
    │
    ├── Parse payload
    ├── Update internal state
    └── async_write_ha_state()
```

### Command Flow

```
HA Service Call (e.g., turn_on)
    │
    ▼
Entity.async_turn_on()
    │
    ▼
Entity.publish(topic, payload)
    │
    ▼
Coordinator.publish()
    │
    ▼
AmpioMQTTClient.async_publish()
    │
    ▼
Ampio Server receives command
```

## Module Type System

Modules are identified by type code. Each type has a dedicated handler class:

```python
CLASS_FACTORY = {
    44: MSENSModuleInfo,      # M-SENS
    33: MDOT2ModuleInfo,      # M-DOT-2
    5: MDIM8sModuleInfo,      # M-DIM-8s
    3: MROL4sModuleInfo,      # M-ROL-4s
    25: MCONModuleInfo,       # M-CON (Satel)
    # ... more types
    -1: GenericModuleInfo,    # Fallback for unknown types
}
```

Each module info class implements `update_configs()` to generate entity configurations based on the module's capabilities.

## Extension Points

### Adding New Module Types

1. Create new class inheriting from `AmpioModuleInfo`
2. Implement `update_configs()` method
3. Add to `CLASS_FACTORY` with type code
4. Create appropriate entity config class if needed

### Adding New Entity Types

1. Create platform file (e.g., `new_platform.py`)
2. Add to `COMPONENTS` in `const.py`
3. Create entity class inheriting from `AmpioEntity`
4. Implement `subscribe_topics()` for state updates
5. Create config class in `models.py`

## Error Handling

- MQTT disconnections are handled with automatic reconnection
- Parse errors are logged at WARNING level and don't crash entities
- Unknown module types fall back to generic handler
- JSON decode errors are caught with specific exception handling
