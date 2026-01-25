# Frequently Asked Questions

## General Questions

### What is the Ampio integration?

The Ampio integration connects Home Assistant to [Ampio Smart Home](https://ampio.pl) systems via MQTT. It automatically discovers all Ampio modules and creates corresponding Home Assistant entities for sensors, lights, switches, covers, and more.

### Is this the official Ampio integration?

This is a custom integration, not the built-in Home Assistant Ampio integration. It provides enhanced functionality and supports more module types. When installed, it takes precedence over any built-in integration with the same domain.

### What Ampio MQTT Bridge version is required?

Version 3.41.2 or later is required. Check your version in the Ampio Smart Home application or in the Home Assistant logs after connecting.

### Does this work without Ampio Server?

No. The integration requires the Ampio Server as the MQTT broker and gateway to the CAN bus. There's no direct module communication - all data flows through the Ampio Server's MQTT Bridge.

---

## Installation

### How do I install via HACS?

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three-dot menu → **Custom repositories**
4. Add `https://github.com/mateuszchrobok/ampio-hacc` as an Integration
5. Search for "Ampio" and click **Install**
6. Restart Home Assistant

### How do I install manually?

1. Download the latest release from GitHub
2. Copy the `custom_components/ampio` folder to your HA config directory
3. Restart Home Assistant

### How do I update the integration?

**Via HACS:** Go to HACS > Integrations > Ampio > Update

**Manual:** Replace the `custom_components/ampio` folder with the new version

---

## Configuration

### What credentials do I use?

Use the admin credentials from the Ampio Smart Home application:
- **Username:** Usually `admin`
- **Password:** The admin password configured in Ampio

### What is the default MQTT port?

The default port is 1883. You typically don't need to change this unless your Ampio Server is configured differently.

### Can I use multiple Ampio Servers?

Currently, the integration supports a single Ampio Server connection per Home Assistant instance. Multiple servers would require separate HA instances.

### How do I change the connection settings?

1. Go to **Settings > Devices & Services > Ampio**
2. Click **Configure**
3. Update the settings

Or remove and re-add the integration with new settings.

---

## Modules and Entities

### How do I find the MAC address of my modules?

The MAC address (user_mac) appears in:
- Entity attributes (`ampio_topic` contains the MAC)
- Ampio Smart Home application under module properties
- Device info in Home Assistant

### Why are some entities missing?

Possible reasons:
1. **Item names not configured:** Configure names in Ampio application
2. **Unsupported module type:** Check logs for "Unknown module type"
3. **PCB version limitation:** Some sensors depend on PCB version (e.g., CO2 requires M-SENS PCB >= 4)
4. **Discovery incomplete:** Reload the integration

### What's the difference between M-SENS variants?

| Variant | PCB | Sensors |
|---------|-----|---------|
| M-SENS-1 | < 3 | Temperature only |
| M-SENS | 3 | Temperature, humidity, pressure, noise, illuminance, air quality |
| M-SENS-CO2 | >= 4 | All above + CO2 |

### Why do touch panels create two entities per button?

Touch panels (M-DOT) create:
1. **binary_sensor:** For on/off state (backwards compatibility)
2. **event:** For button press/release events (recommended for automations)

This provides flexibility for different automation needs.

### How do I control covers with both position and tilt?

Use the standard Home Assistant cover services:

```yaml
service: cover.set_cover_position
target:
  entity_id: cover.ampio_aabb_co1
data:
  position: 50
```

```yaml
service: cover.set_cover_tilt_position
target:
  entity_id: cover.ampio_aabb_co1
data:
  tilt_position: 45
```

### How are alarm zones configured?

Zones are configured in the Ampio application with name prefixes:
- `A:Zone Name` - Away mode only
- `H:Zone Name` - Home mode only
- `B:Zone Name` - Both modes
- `Zone Name` (no prefix) - Away mode only

---

## Device Classes

### How do I set the device class for an entity?

Device classes are determined by name prefixes in Ampio:
- `T:Kitchen` → temperature
- `M:Hallway` → motion
- `D:Front Door` → door
- `L:Ceiling` → light

See [Entity Reference](ENTITIES.md#device-class-prefixes) for the full list.

### Can I change the device class after discovery?

Yes, you can customize entities in Home Assistant:
1. Go to **Settings > Devices & Services > Entities**
2. Find the entity
3. Click the settings icon
4. Change the device class

---

## Automations

### How do I trigger an automation from a button press?

**Using event entity (recommended):**

```yaml
automation:
  trigger:
    - platform: state
      entity_id: event.ampio_aabb_event1
  action:
    # Your actions
```

**Using binary sensor:**

```yaml
automation:
  trigger:
    - platform: state
      entity_id: binary_sensor.ampio_aabb_i1
      to: "on"
  action:
    # Your actions
```

### Can I use Ampio flags in automations?

Yes, flags appear as switch entities:

```yaml
automation:
  trigger:
    - platform: state
      entity_id: switch.ampio_aabb_f1
      to: "on"
  action:
    # Your actions
```

### How do I create a scene with Ampio devices?

Use Home Assistant scenes:

```yaml
scene:
  - name: "Movie Night"
    entities:
      light.ampio_aabb_a1:
        state: on
        brightness: 50
      cover.ampio_bbcc_co1:
        state: closed
```

---

## Performance

### How often does the integration poll for updates?

It doesn't poll! The integration uses MQTT push messaging. States update instantly when changes occur on the Ampio system.

### Why is there a delay when controlling devices?

Delays can be caused by:
- Network latency
- CAN bus traffic
- MQTT broker load

Typically, commands execute within 100-200ms.

### Does this integration affect Home Assistant performance?

The integration has minimal impact:
- No polling overhead
- Efficient MQTT subscriptions
- Lazy entity loading

---

## Compatibility

### Does this work with Home Assistant Cloud (Nabu Casa)?

Yes, the integration works with Nabu Casa for remote access. Ampio devices can be controlled through Google Home or Alexa via Nabu Casa.

### Is this compatible with ESPHome/Zigbee/Z-Wave?

Yes, Ampio entities work alongside other integrations. You can create automations that combine Ampio devices with ESPHome, Zigbee, Z-Wave, or any other integration.

### Does this support Home Assistant Energy Dashboard?

Sensors with appropriate device classes (energy, power) will appear in the Energy Dashboard. For M-IN-IMP4s pulse counters, you may need to customize the unit of measurement.

---

## Development

### How do I add support for a new module type?

See [Platform Development Guide](PLATFORM_GUIDE.md) for detailed instructions. Briefly:
1. Create a module info class in `models.py`
2. Add to `CLASS_FACTORY`
3. Implement `update_configs()` method

### How do I run tests?

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

See [Testing Guide](TESTING.md) for more details.

### Where do I report bugs?

Open an issue at: https://github.com/mateuszchrobok/ampio-hacc/issues

Include:
- Home Assistant version
- Integration version
- Debug logs
- Steps to reproduce

---

## Migration

### I'm upgrading from the original kstaniek/ampio-hacc

This fork is backwards compatible. After upgrading:
1. Entities should retain their IDs
2. Automations should continue working
3. New module types may discover additional entities

### I'm switching from the built-in Ampio integration

1. Remove the built-in integration first
2. Clear any orphaned entities
3. Install this custom integration via HACS
4. Add the integration with your credentials

---

## Security

### Is the MQTT connection encrypted?

By default, no. The connection uses plain MQTT on port 1883. For encrypted connections (port 8883), you would need to configure TLS on your Ampio Server.

### Are my credentials stored securely?

Credentials are stored in Home Assistant's encrypted configuration storage, following HA security best practices.

### Can others on my network control Ampio devices?

Anyone with access to your MQTT broker (Ampio Server) and credentials can control devices. Ensure your network is secured and credentials are not shared.
