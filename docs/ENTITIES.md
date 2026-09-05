# Entity Reference

This document describes all Home Assistant entities created by the Ampio integration.

## Entity Naming Convention

All entities follow this naming pattern:

```
{domain}.ampio_{mac}_{type}{index}
```

Where:
- `domain`: The HA domain (sensor, light, switch, etc.)
- `mac`: The module's user-assigned MAC address (uppercase)
- `type`: Item type code (t, i, o, a, f, etc.)
- `index`: 1-based item index

**Example**: `sensor.ampio_aabb_t1` (Temperature sensor #1 on module AABB)

## Supported Modules and Entities

### Environmental Sensors

#### M-SENS (Code 44)

Multi-sensor environmental module. Entity availability depends on PCB version:

| PCB Version | Variant | Description |
|-------------|---------|-------------|
| < 3 | M-SENS-1 | Basic (temperature only) |
| 3 | M-SENS | Standard (T/H/P/Noise/Illuminance/IAQ) |
| >= 4 | M-SENS-CO2 | Full (adds CO2 sensor) |

**Entities created (PCB >= 3):**

| Entity ID Pattern | Device Class | Unit | Topic |
|-------------------|--------------|------|-------|
| `sensor.ampio_{mac}_t1` | temperature | °C | `state/t/1` |
| `sensor.ampio_{mac}_h1` | humidity | % | `state/au16l/1` |
| `sensor.ampio_{mac}_ps1` | pressure | hPa | `state/au16l/6` |
| `sensor.ampio_{mac}_n1` | signal_strength | dB | `state/au16l/3` |
| `sensor.ampio_{mac}_i1` | illuminance | lx | `state/au16l/4` |
| `sensor.ampio_{mac}_aq1` | aqi | - | `state/au16l/5` |
| `sensor.ampio_{mac}_co21` | carbon_dioxide | ppm | `state/au16l/7` (PCB >= 4 only) |

#### M-SENS-LITE (Code 45)

Simplified environmental sensor with temperature and humidity only.

| Entity ID Pattern | Device Class | Unit | Topic |
|-------------------|--------------|------|-------|
| `sensor.ampio_{mac}_t1` | temperature | °C | `state/t/1` |
| `sensor.ampio_{mac}_h1` | humidity | % | `state/au16l/1` |

#### METEO-1s (Code 34)

Outdoor weather station module.

| Entity ID Pattern | Device Class | Unit | Topic |
|-------------------|--------------|------|-------|
| `sensor.ampio_{mac}_t1` | temperature | °C | `state/t/1` |
| `sensor.ampio_{mac}_h1` | humidity | % | `state/au16l/1` (if au > 0) |

---

### Touch Panels (M-DOT Series)

Touch panels create both binary sensors (for state) and event entities (for press/release events).

| Module | Code | Buttons | Description |
|--------|------|---------|-------------|
| M-DOT-2 | 33 | 2 | 2-field touch panel |
| M-DOT-4 | 8 | 4 | 4-field touch panel |
| M-DOT-6 | 6 | 6 | 6-field touch panel with display |
| M-DOT-9 | 11 | 9 | 9-field touch panel |
| M-DOT-15LCD | 27 | 15 | 15-field touch panel with LCD |
| M-DOT-18 | 18 | 18 | 18-field touch panel |

**Entities created (per button):**

| Entity ID Pattern | Platform | Device Class | Topic |
|-------------------|----------|--------------|-------|
| `binary_sensor.ampio_{mac}_i{n}` | binary_sensor | opening | `state/i/{n}` |
| `event.ampio_{mac}_event{n}` | event | button | `state/i/{n}` |

---

### Relay Modules

#### M-PR-8s (Code 4)

8-channel relay module with binary inputs.

**Output entities** - created based on item name prefix:

| Name Prefix | Platform | Entity ID Pattern |
|-------------|----------|-------------------|
| `L:` (light) | light | `light.ampio_{mac}_a{n}` |
| Other | switch | `switch.ampio_{mac}_bo{n}` |

**Input entities:**

| Entity ID Pattern | Platform | Topic |
|-------------------|----------|-------|
| `binary_sensor.ampio_{mac}_i{n}` | binary_sensor | `state/i/{n}` |

#### M-REL-2s (Code 7)

2-channel relay module. Same entity logic as M-PR-8s.

#### M-REL-10s (Code 9)

10-channel relay module. Same entity logic as M-PR-8s.

---

### Dimmer Modules

#### M-DIM-8s (Code 5)

8-channel dimmer module.

| Entity ID Pattern | Platform | Features | Topics |
|-------------------|----------|----------|--------|
| `light.ampio_{mac}_a{n}` | light | brightness | State: `state/o/{n}`, `state/a/{n}`<br>Command: `o/{n}/cmd` |

#### M-DIM-1p (Code 13)

1-channel flush-mount dimmer. Same entity structure as M-DIM-8s.

#### M-DIM-2s (Code 14)

2-channel DIN rail dimmer. Same entity structure as M-DIM-8s.

---

### LED Controllers

#### M-LED-1 (Code 17)

LED controller module with dimmable outputs.

| Entity ID Pattern | Platform | Features | Icon |
|-------------------|----------|----------|------|
| `light.ampio_{mac}_a{n}` | light | brightness | mdi:spotlight |

#### M-LED-s (Code 19)

OWA lighting bus controller (DIN rail). Same structure as M-LED-1.

---

### RGB/RGBW Controllers

#### M-RGBu-1 (Code 12)

RGBW LED controller.

| Entity ID Pattern | Platform | Features | Topics |
|-------------------|----------|----------|--------|
| `light.ampio_{mac}_rgbw1` | light | rgb, white | State: `state/rgbw/1`, `state/a/4`<br>Command: `rgbw/1/cmd`, `o/4/cmd` |

#### WL-OC-RGBW1p (Code 58)

Wireless RGBW controller. Same structure as M-RGBu-1.

---

### Cover Modules

#### M-ROL-4s (Code 3)

4-channel roller shutter controller.

| Entity ID Pattern | Platform | Device Class | Features |
|-------------------|----------|--------------|----------|
| `cover.ampio_{mac}_co{n}` | cover | shutter (default) | position, tilt |

**Topic mapping:**

| Feature | Topic |
|---------|-------|
| Position state | `state/a/{n}` |
| Closing state | `state/o/{2*(n-1)+1}` |
| Opening state | `state/o/{2*n}` |
| Tilt state | `state/a/{6+n}` |
| Commands | `o/{n}/cmd`, `raw` |

**Device class from name prefix:**

| Prefix | Device Class | Icon |
|--------|--------------|------|
| `VA:` | valve | mdi:valve |
| `G:` | garage | - |
| `BL:` | blind | - |
| (default) | shutter | - |

#### WL-REL-ROL1p (Code 57)

Wireless roller shutter module. Same structure as M-ROL-4s.

---

### Climate Controllers

#### M-RT-16s (Code 22)

16-zone heating/cooling controller.

| Entity ID Pattern | Platform | Features |
|-------------------|----------|----------|
| `climate.ampio_{mac}_climate{n}` | climate | temperature, setpoint, mode |

**Topic mapping:**

| Feature | State Topic | Command Topic |
|---------|-------------|---------------|
| Current temperature | `state/t/{n}` | - |
| Setpoint | `state/rs/{n}` | `rs/{n}/cmd` |
| Mode | `state/rm/{n}` | `rm/{n}/cmd` |

**Climate modes:**

| Value | Mode |
|-------|------|
| 0 | Calendar |
| 1 | Manual Day |
| 2 | Manual Night |
| 3 | Holidays |
| 4 | Block |

#### M-RT-s (Code 23)

Temperature controller. Same structure as M-RT-16s.

---

### Server Module

#### M-SERV-3s (Code 10)

Server module with flags and I/O.

| Entity Type | Entity ID Pattern | Topic |
|-------------|-------------------|-------|
| Switch (outputs) | `switch.ampio_{mac}_bo{n}` | `state/o/{n}` |
| Binary sensor (inputs) | `binary_sensor.ampio_{mac}_i{n}` | `state/i/{n}` |
| Switch (flags) | `switch.ampio_{mac}_f{n}` | `state/f/{n}` |

---

### Integration Modules

#### M-CON (Code 25)

Generic integration bridge. The firmware decides what it talks to, and only the
INTEGRA build — `soft_ver % 100 == 1` — bridges a Satel alarm panel. Every other
M-CON in a project is a serial master for something else (Modbus RTU, RS-485,
weather station) and publishes no Satel topics at all, so no Satel entities are
created for it even when the project allocates Satel rows on it.

**Binary sensors** (Satel zones, INTEGRA firmware only):

| Entity ID Pattern | Platform | Topic |
|-------------------|----------|-------|
| `binary_sensor.ampio_{mac}_bi{n}` | binary_sensor | `state/bi/{n}` |

Zone names come from the project database's `satel_wej` rows. Ampio Designer
pre-allocates those rows in bulk and leaves them nameless, so **only named rows
become entities** — see [Satel zone entity count](#satel-zone-entity-count).

Zones get **no device class** by default: nothing in the protocol or the project
says whether a zone is a motion detector, a door reed or a tamper loop. To declare
one, prefix the object's name in Ampio Designer, e.g. `M:PIR Salon` for motion or
`D:Drzwi garaż` for a door — the same prefix mechanism every other item type uses.

To work out which a zone is, watch its **pulse shape** rather than its level:

```
mosquitto_sub -h <ampio-server> -t 'ampio/from/<mac>/state/bi/+' -v
```

A motion detector pulses repeatedly for a few seconds at a time while someone is in
the room; over one 20-minute window on the reference installation the PIR zones
produced 49 high runs of 3–42 s (median 8 s). A door or gate contact makes one long
transition per physical movement — 25 s, 53 s and 121 s there — and may idle high
when closed rather than low. Zones matching neither shape exist: one unnamed zone
there went high once for 336 s.

**Alarm control panel:**

| Entity ID Pattern | Platform |
|-------------------|----------|
| `alarm_control_panel.ampio_{mac}_alarm` | alarm_control_panel |

**Zone configuration from name prefix:**

| Prefix | Zone Type |
|--------|-----------|
| `A:` | Away only |
| `H:` | Home only |
| `B:` | Both (Away + Home) |
| (none) | Away only |

Satel **outputs** (`satel_wyj`, `state/bo/{n}`) and per-zone **alarm state**
(`satel_alarm`) are not exposed. The alarm panel entity already carries arm and
alarm state; what the output index means is not established.

##### Satel zone entity count

`satel_wej` is normally the largest row type in an Ampio project by an order of
magnitude, and nearly all of it is unused allocation. On the reference
installation the objects table holds **2403** `satel_wej` rows and this
integration creates **15** binary sensors from them. Three filters do that, all
of them pre-existing and shared with every other item type:

| Filter | Effect on the reference project |
|--------|--------------------------------|
| Name must not be blank or a placeholder | 2403 → 19 |
| `funkcja` (index) must be ≥ 1 | 19 → 18 |
| First row to claim an index wins | 18 → 15 |
| Module firmware must be INTEGRA | all 15 already sit on the one Satel bridge |

If a change to this integration ever makes a project produce hundreds of `bi`
sensors that sit at `unknown`, one of these filters was weakened.

---

### Input Modules

#### M-IN-8s (Code 37)

8 binary inputs (DIN rail).

| Entity ID Pattern | Platform | Topic |
|-------------------|----------|-------|
| `binary_sensor.ampio_{mac}_i{n}` | binary_sensor | `state/i/{n}` |

#### M-IN-16s (Code 39)

16 binary inputs. Same structure as M-IN-8s.

#### M-IN-2p (Code 40)

2 binary inputs (flush-mount). Same structure as M-IN-8s.

#### M-IN-11p (Code 41)

11 binary inputs. Same structure as M-IN-8s.

#### M-IN-AC4s (Code 47)

4 AC voltage inputs. Same structure as M-IN-8s.

#### M-IN-AD8s (Code 42)

8 analog inputs (0-10V or 4-20mA).

| Entity ID Pattern | Platform | Topic |
|-------------------|----------|-------|
| `sensor.ampio_{mac}_ain{n}` | sensor | `state/a/{n}` |

#### M-IN-IMP4s (Code 43)

4 pulse counter inputs for energy/water meters.

| Entity ID Pattern | Platform | Device Class | Topic |
|-------------------|----------|--------------|-------|
| `sensor.ampio_{mac}_cnt{n}` | sensor | energy | `state/au32/{n}` |

#### M-IN-TCD3p (Code 46)

3 NTC temperature sensor inputs.

| Entity ID Pattern | Platform | Device Class | Topic |
|-------------------|----------|--------------|-------|
| `sensor.ampio_{mac}_t{n}` | sensor | temperature | `state/t/{n}` |

---

### Output Modules

#### M-OC-4 (Code 26)

4 open collector outputs (dimmable).

| Entity ID Pattern | Platform | Features |
|-------------------|----------|----------|
| `light.ampio_{mac}_a{n}` | light | brightness |

#### M-OC-8s (Code 35)

8 open collector outputs. Same structure as M-OC-4.

#### M-OC-32s (Code 36)

32 open collector outputs. Same structure as M-OC-4.

---

### Combo Modules

#### M-INOC-4p (Code 48)

4 binary inputs + 4 OC outputs + RGBW controller.

| Entity Type | Entity ID Pattern |
|-------------|-------------------|
| Binary sensor (inputs) | `binary_sensor.ampio_{mac}_i{n}` |
| Light (outputs) | `light.ampio_{mac}_a{n}` |
| Light (RGBW) | `light.ampio_{mac}_rgbw1` (if au >= 4) |

#### M-INOC-8s (Code 50)

8 binary inputs + 8 OC outputs.

| Entity Type | Entity ID Pattern |
|-------------|-------------------|
| Binary sensor (inputs) | `binary_sensor.ampio_{mac}_i{n}` |
| Light (outputs) | `light.ampio_{mac}_a{n}` |

---

### Wireless Modules

#### WL-REL-2p (Code 56)

Wireless 2-relay module.

| Entity ID Pattern | Platform | Topic |
|-------------------|----------|-------|
| `switch.ampio_{mac}_bo{n}` | switch | `state/o/{n}` |

#### WZ-SENS-TMP-p (Code 59)

Wireless temperature sensor.

| Entity ID Pattern | Platform | Device Class | Topic |
|-------------------|----------|--------------|-------|
| `sensor.ampio_{mac}_t{n}` | sensor | temperature | `state/t/{n}` |

---

### Other Modules

#### M-WRC (Code 49)

Wireless remote control.

| Entity ID Pattern | Platform | Topic |
|-------------------|----------|-------|
| `binary_sensor.ampio_{mac}_i{n}` | binary_sensor | `state/i/{n}` |

#### M-RDN-1s (Code 38)

Dimmer/RGB driver module.

| Entity ID Pattern | Platform | Features |
|-------------------|----------|----------|
| `light.ampio_{mac}_a{n}` | light | brightness |

#### M-ALARM-8s (Code 53)

8-zone alarm control panel.

| Entity ID Pattern | Platform | Topic |
|-------------------|----------|-------|
| `binary_sensor.ampio_{mac}_i{n}` | binary_sensor | `state/i/{n}` |

---

## Device Class Prefixes

When naming items in Ampio, you can use prefixes to set the device class:

| Prefix | Device Class | Example Name |
|--------|--------------|--------------|
| `T:` | temperature | `T:Kitchen` |
| `H:` | humidity | `H:Bathroom` |
| `M:` | motion | `M:Hallway` |
| `D:` | door | `D:Front Door` |
| `W:` | window | `W:Bedroom` |
| `L:` | light | `L:Ceiling` |
| `O:` | opening | `O:Gate` |
| `P:` | plug | `P:TV` |
| `S:` | safety | `S:Smoke` |
| `V:` | vibration | `V:Safe` |
| `VA:` | valve | `VA:Water` |
| `G:` | garage | `G:Main` |
| `BL:` | blind | `BL:Living Room` |
| `HE:` | heat | `HE:Floor Heating` |

---

## Extra State Attributes

All Ampio entities include an `ampio_topic` attribute showing the MQTT topic path:

```yaml
ampio_topic: "aabb/t/1"
```

This helps with debugging and understanding which MQTT topic the entity subscribes to.

---

## 8-bit Analog Flags (`afu8`)

Any module whose project entry contains a `bit8` object gets one writable
`number` entity per flag. These are cross-cutting rather than tied to a module
type, so they do not appear in the per-module tables above.

| Entity ID Pattern | Platform | Range | State Topic | Write |
|-------------------|----------|-------|-------------|-------|
| `number.ampio_{mac}_afu8_{index}` | number | 0-255 (step 1) | `state/afu8/{index}` | raw CAN, see below |

The range narrows to the project's own `min`/`max` when it defines a usable
sub-range of 0-255; otherwise the full byte range is used.

Writes do **not** go to a `/cmd` topic — no such topic exists for `afu8`. The
value is sent as a raw CAN broadcast on `ampio/to/{mac}/raw` with the payload
`7AF9` + value byte + 0-based index byte, as ASCII hex. See
[MQTT_PROTOCOL.md](MQTT_PROTOCOL.md#analog-flags-8-bit).

16-bit flags (`bit16` / `afi16`) are **not** exposed. Their state topic is live,
but no write format for them is attested anywhere, so exposing them writable
would mean guessing a CAN frame at real hardware.

---

## Generic Module Fallback

For unknown module types, the integration uses a generic handler that:

1. Creates `binary_sensor` entities for all binary inputs
2. Creates `switch` entities for binary outputs (or `light` if name has `L:` prefix)
3. Creates `sensor` entities for temperature inputs

A warning is logged when a module uses the generic fallback:

```
Unknown module type 99 (99) detected. Using generic handler.
Consider adding explicit support for this module.
```
