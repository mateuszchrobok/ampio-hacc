# Ampio MQTT Protocol

This document describes the MQTT topic structure and payload formats used by the Ampio Smart Home system.

## Topic Structure

All topics follow the pattern: `ampio/{direction}/{target}/{path}`

- `direction`: `to` (commands) or `from` (states/responses)
- `target`: MAC address (uppercase) or special keyword
- `path`: Item type and index

## Discovery Topics

### Server Version

Request:
```
Topic: ampio/to/info/version
Payload: (empty)
```

Response:
```
Topic: ampio/from/info/version
Payload: {"version": "3.41.2"}
```

### Device List

Request:
```
Topic: ampio/to/can/dev/list
Payload: "1"
```

Response:
```
Topic: ampio/from/can/dev/list
Payload: {
  "s": 1,
  "d": [
    {
      "mac": "1B88",
      "user_mac": "AABB",
      "typ": 44,
      "pcb": 3,
      "soft_ver": 341,
      "protocol": 1,
      "date_prod": 20230601,
      "i": 8,
      "o": 4,
      "a": 8,
      "au": 8,
      "t": 1,
      "f": 16,
      "name": "base64_encoded_name"
    }
  ]
}
```

Fields:
- `mac`: CAN bus MAC address
- `user_mac`: User-assigned MAC (used in topics)
- `typ`: Module type code
- `pcb`: PCB version
- `soft_ver`: Firmware version
- `protocol`: Protocol version
- `i`: Number of binary inputs
- `o`: Number of binary outputs
- `a`: Number of analog inputs
- `au`: Number of analog outputs
- `t`: Number of temperature sensors
- `f`: Number of flags
- `name`: Base64-encoded module name

### Module Description

Request:
```
Topic: ampio/to/{mac}/description
Payload: "1"
```

Response:
```
Topic: ampio/from/{mac}/description
Payload: {
  "s": 1,
  "d": [
    {
      "t": "t",
      "n": 1,
      "d": "VDpUZW1wZXJhdHVyZQ=="
    },
    {
      "t": "i",
      "n": 1,
      "d": "TTpNb3Rpb24="
    }
  ]
}
```

Fields:
- `t`: Item type (see Item Types below)
- `n`: Item index (1-based)
- `d`: Base64-encoded name with optional device class prefix

Name format: `PREFIX:Name` where PREFIX defines device class:
- `T`: Temperature
- `M`: Motion
- `D`: Door
- `W`: Window
- `L`: Light
- `H`: Home zone (alarm)
- `A`: Away zone (alarm)
- `B`: Both zones (alarm)

## State Topics

### Binary States

```
Topic: ampio/from/{mac}/state/i/{index}   (binary input)
Topic: ampio/from/{mac}/state/o/{index}   (binary output)
Topic: ampio/from/{mac}/state/f/{index}   (flag)
Payload: "0" or "1"
```

### Temperature

```
Topic: ampio/from/{mac}/state/t/{index}
Payload: "21.5"  (decimal value in Celsius)
```

### Analog Values

```
Topic: ampio/from/{mac}/state/a/{index}      (8-bit: 0-255)
Topic: ampio/from/{mac}/state/au/{index}     (8-bit: 0-255)
Topic: ampio/from/{mac}/state/au16/{index}   (16-bit unsigned)
Topic: ampio/from/{mac}/state/au16l/{index}  (16-bit /10: 0-6553.6)
Topic: ampio/from/{mac}/state/au32/{index}   (32-bit unsigned)
Payload: numeric value as string
```

### RGB/RGBW

```
Topic: ampio/from/{mac}/state/rgbw/{index}
Payload: "255,128,0"  (comma-separated R,G,B or R,G,B,W)
```

### Climate (M-RT modules)

```
Topic: ampio/from/{mac}/state/rs/{index}    (setpoint)
Topic: ampio/from/{mac}/state/rm/{index}    (mode: 0-4)
Payload: numeric value
```

Mode values:
- 0: Calendar
- 1: Manual Day
- 2: Manual Night
- 3: Holidays
- 4: Block

### Alarm States (M-CON with Satel)

```
Topic: ampio/from/{mac}/state/armed/{index}
Topic: ampio/from/{mac}/state/alarm/{index}
Topic: ampio/from/{mac}/state/entrytime/{index}
Topic: ampio/from/{mac}/state/exittime/{index}
Topic: ampio/from/{mac}/state/exittime10/{index}
Payload: "0" or "1"
```

## Command Topics

### Binary Outputs

```
Topic: ampio/to/{mac}/o/{index}/cmd
Payload: "0" (off) or "1" (on)
```

### Flags

```
Topic: ampio/to/{mac}/f/{index}/cmd
Payload: "0" or "1"
```

### Dimmers

```
Topic: ampio/to/{mac}/o/{index}/cmd
Payload: "0" - "255"  (brightness level)
```

### RGB/RGBW

```
Topic: ampio/to/{mac}/rgbw/{index}/cmd
Payload: "255,128,0" or "off"
```

### Covers

Simple commands:
```
Topic: ampio/to/{mac}/o/{index}/cmd
Payload: "0" (stop), "1" (close), "2" (open)
```

Position/tilt via raw command:
```
Topic: ampio/to/{mac}/raw
Payload: hex_string
```

Raw command format for position:
```
00 01 {mask} {position} {tilt}
```
- mask: Bitmask for channels (e.g., 01 for channel 1)
- position: 0-100 (0x00-0x64)
- tilt: 0-100 or 0x66 for keep previous

Raw command format for tilt only:
```
00 02 {mask} {tilt}
```

### Climate Setpoint

```
Topic: ampio/to/{mac}/rs/{index}/cmd
Payload: "21.5"  (temperature value)
```

### Climate Mode

```
Topic: ampio/to/{mac}/rm/{index}/cmd
Payload: "0" - "4"  (mode value)
```

### Alarm Commands (M-CON with Satel)

```
Topic: ampio/to/{mac}/raw
Payload: {cmd}{zone_mask_hex}
```

Command prefixes:
- `1E0080`: Arm zones
- `1E0084`: Disarm zones
- `1E0085`: Clear alarm

Zone mask: 4-byte little-endian bitmask of zones (hex encoded)

Example: Arm zones 1, 2, 3:
```
1E008007000000
```
(0x07 = 0b00000111 = zones 1, 2, 3)

## Module Type Codes

| Code | Module | Description |
|------|--------|-------------|
| 3 | M-ROL-4s | 4-channel roller shutter |
| 4 | M-PR-8s | 8-channel relay |
| 5 | M-DIM-8s | 8-channel dimmer |
| 6 | M-DOT-6 | 6-field touch panel |
| 7 | M-REL-2s | 2-channel relay |
| 8 | M-DOT-4 | 4-field touch panel |
| 9 | M-REL-10s | 10-channel relay |
| 10 | M-SERV-3s | Server module |
| 11 | M-DOT-9 | 9-field touch panel |
| 12 | M-RGBu-1 | RGBW controller |
| 17 | M-LED-1 | LED controller |
| 22 | M-RT-16s | 16-zone heating controller |
| 25 | M-CON | Integration module (Satel) |
| 33 | M-DOT-2 | 2-field touch panel |
| 44 | M-SENS | Environmental sensor |
| 45 | M-SENS-LITE | Basic environmental sensor |

For a complete list, see `TYPE_CODES` in `models.py`.

## M-SENS Variants

M-SENS modules have different capabilities based on PCB version:

| PCB Version | Variant | Sensors |
|-------------|---------|---------|
| < 3 | M-SENS-1 | Temperature only (au32) |
| 3 | M-SENS | T, H, P, Noise, Illuminance, IAQ |
| >= 4 | M-SENS-CO2 | All above + CO2 |

Sensor topic mapping for PCB >= 3:
- Temperature: `state/t/1`
- Humidity: `state/au16l/1`
- Pressure: `state/au16l/6`
- Noise: `state/au16l/3`
- Illuminance: `state/au16l/4`
- Air Quality: `state/au16l/5`
- CO2 (PCB >= 4): `state/au16l/7`
