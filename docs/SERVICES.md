# Service Reference

This document describes how to control Ampio devices through Home Assistant services and direct MQTT commands.

## Standard Home Assistant Services

The Ampio integration creates standard Home Assistant entities that respond to platform-specific services.

### Light Services

```yaml
# Turn on a light
service: light.turn_on
target:
  entity_id: light.ampio_aabb_a1
data:
  brightness: 255  # 0-255 for dimmers

# Turn off
service: light.turn_off
target:
  entity_id: light.ampio_aabb_a1
```

**RGB/RGBW lights:**

```yaml
service: light.turn_on
target:
  entity_id: light.ampio_aabb_rgbw1
data:
  rgb_color: [255, 128, 0]  # Orange
  white_value: 128  # For RGBW modules
```

### Switch Services

```yaml
# Turn on
service: switch.turn_on
target:
  entity_id: switch.ampio_aabb_bo1

# Turn off
service: switch.turn_off
target:
  entity_id: switch.ampio_aabb_bo1

# Toggle
service: switch.toggle
target:
  entity_id: switch.ampio_aabb_bo1
```

### Cover Services

```yaml
# Open cover
service: cover.open_cover
target:
  entity_id: cover.ampio_aabb_co1

# Close cover
service: cover.close_cover
target:
  entity_id: cover.ampio_aabb_co1

# Stop cover
service: cover.stop_cover
target:
  entity_id: cover.ampio_aabb_co1

# Set position (0 = closed, 100 = open)
service: cover.set_cover_position
target:
  entity_id: cover.ampio_aabb_co1
data:
  position: 50

# Set tilt (for blinds)
service: cover.set_cover_tilt_position
target:
  entity_id: cover.ampio_aabb_co1
data:
  tilt_position: 45
```

### Climate Services

```yaml
# Set temperature
service: climate.set_temperature
target:
  entity_id: climate.ampio_aabb_climate1
data:
  temperature: 21.5

# Set HVAC mode
service: climate.set_hvac_mode
target:
  entity_id: climate.ampio_aabb_climate1
data:
  hvac_mode: heat  # or 'off'
```

### Alarm Control Panel Services

```yaml
# Arm away
service: alarm_control_panel.alarm_arm_away
target:
  entity_id: alarm_control_panel.ampio_aabb_alarm

# Arm home
service: alarm_control_panel.alarm_arm_home
target:
  entity_id: alarm_control_panel.ampio_aabb_alarm

# Disarm
service: alarm_control_panel.alarm_disarm
target:
  entity_id: alarm_control_panel.ampio_aabb_alarm
data:
  code: "1234"  # If required
```

---

## Direct MQTT Commands

For advanced control, you can publish directly to Ampio MQTT topics using Home Assistant's MQTT integration.

### Topic Format

```
ampio/to/{mac}/{item_type}/{index}/cmd
```

Where:
- `{mac}`: Module's user MAC address (uppercase)
- `{item_type}`: Item type code (o, f, rgbw, rs, rm, etc.)
- `{index}`: 1-based item index

### Binary Outputs (Relays, Lights)

```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/o/1/cmd"
  payload: "1"  # 1 = on, 0 = off
```

### Flags

```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/f/1/cmd"
  payload: "1"  # 1 = on, 0 = off
```

### Dimmers

```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/o/1/cmd"
  payload: "128"  # 0-255 brightness
```

### RGB/RGBW Colors

```yaml
# Set RGB color
service: mqtt.publish
data:
  topic: "ampio/to/AABB/rgbw/1/cmd"
  payload: "255,128,0"  # R,G,B values

# Turn off
service: mqtt.publish
data:
  topic: "ampio/to/AABB/rgbw/1/cmd"
  payload: "off"
```

### Climate Setpoint

```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/rs/1/cmd"
  payload: "21.5"  # Temperature in Celsius
```

### Climate Mode

```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/rm/1/cmd"
  payload: "1"  # 0=Calendar, 1=Manual Day, 2=Manual Night, 3=Holidays, 4=Block
```

---

## Raw Commands

Some operations require raw commands sent to the module's `raw` topic.

### Cover Position with Tilt

```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/raw"
  payload: "0001015066"  # Set position 80%, tilt keep previous
```

**Raw command format for position:**
```
00 01 {mask} {position} {tilt}
```

| Byte | Description | Values |
|------|-------------|--------|
| mask | Channel bitmask | 0x01 = ch1, 0x02 = ch2, 0x04 = ch3, etc. |
| position | Position | 0x00 (closed) to 0x64 (100% open) |
| tilt | Tilt angle | 0x00-0x64, or 0x66 = keep previous |

**Example: Set channel 1 to 50% position, 45% tilt:**
```
00 01 01 32 2D
```

### Tilt Only

```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/raw"
  payload: "00020132"  # Set tilt 50% on channel 1
```

**Raw command format:**
```
00 02 {mask} {tilt}
```

### Alarm Commands (Satel via M-CON)

**Arm zones:**
```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/raw"
  payload: "1E008007000000"  # Arm zones 1, 2, 3
```

**Disarm zones:**
```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/raw"
  payload: "1E008407000000"  # Disarm zones 1, 2, 3
```

**Clear alarm:**
```yaml
service: mqtt.publish
data:
  topic: "ampio/to/AABB/raw"
  payload: "1E0085FFFFFFFF"  # Clear all zones
```

**Command prefixes:**

| Prefix | Action |
|--------|--------|
| `1E0080` | Arm zones |
| `1E0084` | Disarm zones |
| `1E0085` | Clear alarm |

**Zone mask** (4 bytes, little-endian hex):

| Zones | Mask |
|-------|------|
| Zone 1 | `01000000` |
| Zone 2 | `02000000` |
| Zone 3 | `04000000` |
| Zones 1-3 | `07000000` |
| All zones | `FFFFFFFF` |

---

## Automation Examples

### Turn on light at sunset

```yaml
automation:
  - alias: "Kitchen light at sunset"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: light.turn_on
        target:
          entity_id: light.ampio_aabb_a1
        data:
          brightness: 200
```

### Close covers on temperature

```yaml
automation:
  - alias: "Close blinds when hot"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ampio_aabb_t1
        above: 25
    action:
      - service: cover.close_cover
        target:
          entity_id: cover.ampio_ccdd_co1
```

### Scene with multiple devices

```yaml
automation:
  - alias: "Movie mode"
    trigger:
      - platform: event
        event_type: ampio_button_press
        event_data:
          entity_id: event.ampio_aabb_event1
    action:
      - service: light.turn_on
        target:
          entity_id: light.ampio_bbcc_a1
        data:
          brightness: 50
      - service: cover.set_cover_position
        target:
          entity_id: cover.ampio_ccdd_co1
        data:
          position: 0
```

### React to touch panel button

```yaml
automation:
  - alias: "Toggle light on button press"
    trigger:
      - platform: state
        entity_id: binary_sensor.ampio_aabb_i1
        to: "on"
    action:
      - service: light.toggle
        target:
          entity_id: light.ampio_bbcc_a1
```

---

## Scripting

### Script to set room ambiance

```yaml
script:
  living_room_ambiance:
    alias: "Living Room Ambiance"
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.ampio_aabb_rgbw1
        data:
          rgb_color: [255, 180, 100]
          white_value: 50
      - service: light.turn_on
        target:
          entity_id: light.ampio_aabb_a1
        data:
          brightness: 80
      - service: cover.set_cover_position
        target:
          entity_id: cover.ampio_bbcc_co1
        data:
          position: 30
```

---

## Developer API

For programmatic control from custom components or AppDaemon:

```python
# Publish via coordinator
coordinator = hass.data[DATA_AMPIO][DATA_AMPIO_COORDINATOR]
await coordinator.async_publish(
    topic="ampio/to/AABB/o/1/cmd",
    payload="1",
    qos=0,
    retain=False
)
```

See [API Reference](API_REFERENCE.md) for full developer documentation.
