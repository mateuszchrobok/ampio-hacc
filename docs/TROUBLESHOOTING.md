# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Ampio Home Assistant integration.

## Quick Diagnostics

### Check Integration Status

1. Go to **Settings > Devices & Services**
2. Find **Ampio** in the integrations list
3. Check the status indicator:
   - Green checkmark: Connected and working
   - Yellow warning: Partial issues
   - Red X: Connection failed

### View Diagnostics

1. Click on the Ampio integration
2. Click the three-dot menu (⋮)
3. Select **Download diagnostics**

This provides a detailed report of:
- Configuration
- Connected modules
- Entity states
- Error counts

---

## Common Issues and Solutions

### No Entities Discovered

**Symptoms:**
- Integration shows as connected but no devices appear
- "0 devices" shown after setup

**Possible Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| MQTT broker unreachable | Check Ampio Server IP and port (default: 1883) |
| Wrong credentials | Verify admin username and password |
| Firewall blocking | Ensure port 1883 is open between HA and Ampio Server |
| MQTT Bridge not running | Check Ampio Server status, restart if needed |
| Outdated MQTT Bridge | Update to version 3.41.2 or later |

**Verify MQTT connectivity:**
```bash
# From command line (mosquitto-clients)
mosquitto_sub -h <ampio_ip> -p 1883 -u admin -P <password> -t "ampio/#" -v
```

### Entities Show "Unavailable"

**Symptoms:**
- Entities appear but show "unavailable" state
- Intermittent availability

**Possible Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Module offline | Check physical module power and CAN bus connection |
| MQTT disconnected | Check HA logs for disconnect messages |
| Module not responding | Restart the specific Ampio module |
| Discovery timeout | Reload the integration |

**Check module status in Ampio:**
1. Open Ampio Smart Home application
2. Go to module diagnostics
3. Verify module is online and communicating

### Commands Not Working

**Symptoms:**
- Turning on/off lights doesn't work
- Cover commands are ignored
- State doesn't change

**Possible Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Wrong topic format | Check entity's `ampio_topic` attribute |
| QoS issues | Try republishing with QoS 1 |
| Module busy | Wait and retry |
| Physical issue | Check physical connections and power |

**Debug by monitoring MQTT traffic:**
```bash
# Subscribe to all Ampio topics
mosquitto_sub -h <ampio_ip> -t "ampio/#" -v

# In another terminal, send a command
mosquitto_pub -h <ampio_ip> -t "ampio/to/AABB/o/1/cmd" -m "1"
```

### Discovery Incomplete

**Symptoms:**
- Some modules are missing
- Only partial entities created

**Possible Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Discovery timeout | Wait longer, reload integration |
| Module not responding | Check specific module status |
| Name not configured | Configure item names in Ampio application |
| Unknown module type | Check logs for "Unknown module type" warning |

**Force re-discovery:**
1. Go to **Settings > Devices & Services > Ampio**
2. Click **Reload**

### Duplicate Entities

**Symptoms:**
- Same entity appears multiple times
- Entity IDs with `_2`, `_3` suffix

**Solution:**
1. Remove the integration completely
2. Delete orphaned entities manually
3. Re-add the integration

### Slow Response Times

**Symptoms:**
- Commands take seconds to execute
- States update slowly

**Possible Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Network latency | Check network between HA and Ampio Server |
| High MQTT traffic | Reduce polling/logging frequency |
| HA performance | Check HA resource usage |
| CAN bus congestion | Reduce automation frequency |

---

## Debug Logging

### Enable Debug Logs

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ampio: debug
```

Then restart Home Assistant.

### View Logs

**Via UI:**
1. Go to **Settings > System > Logs**
2. Filter by "ampio"

**Via command line:**
```bash
# For HA OS/Supervised
ha core logs | grep ampio

# For Docker
docker logs homeassistant 2>&1 | grep ampio

# For Core installation
tail -f ~/.homeassistant/home-assistant.log | grep ampio
```

### Log Messages Reference

| Log Message | Meaning | Action |
|-------------|---------|--------|
| `Connected to Ampio MQTT broker` | Successful connection | Normal |
| `Disconnected from Ampio MQTT broker` | Lost connection | Check network |
| `Unable to connect to MQTT broker` | Connection failed | Verify IP/credentials |
| `All modules discovered` | Discovery complete | Normal |
| `Ignoring duplicate` | Entity already exists | Normal (skipping duplicates) |
| `Unknown module type X detected` | New/unsupported module | Check models.py |
| `Unable to parse JSON` | Invalid MQTT payload | Check Ampio Server |

### MQTT Message Debugging

To see all MQTT messages:

```yaml
logger:
  logs:
    custom_components.ampio.coordinator: debug
```

This shows:
- Received message topics and payloads
- Published commands
- Discovery responses

---

## Network Troubleshooting

### Test MQTT Connectivity

```bash
# Test TCP connection
nc -zv <ampio_ip> 1883

# Test MQTT subscribe
mosquitto_sub -h <ampio_ip> -p 1883 -u admin -P <password> -t "ampio/from/info/version" -C 1

# Test MQTT publish
mosquitto_pub -h <ampio_ip> -p 1883 -u admin -P <password> -t "ampio/to/info/version" -m ""
```

### Firewall Rules

Ensure these ports are open:

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 1883 | TCP | Outbound from HA | MQTT |
| 8883 | TCP | Outbound from HA | MQTT over TLS (if used) |

### DNS Resolution

If using hostname instead of IP:

```bash
# Test DNS resolution
nslookup ampio-server.local
ping ampio-server.local
```

---

## Module-Specific Issues

### M-SENS Sensors Missing

**Issue:** Not all M-SENS sensors appear (e.g., no CO2)

**Cause:** PCB version determines available sensors

**Solution:** Check your M-SENS variant:
- PCB < 3: Temperature only
- PCB = 3: Full sensor suite (no CO2)
- PCB >= 4: Full suite including CO2

### M-DOT Buttons Not Responding

**Issue:** Touch panel presses not detected

**Solutions:**
1. Check binary_sensor entities are created
2. Check event entities for button events
3. Verify item names are configured in Ampio

### M-ROL Cover Position Wrong

**Issue:** Cover shows wrong position or tilt

**Solutions:**
1. Calibrate covers in Ampio application
2. Check if position/tilt topics are correct
3. Verify cover type (shutter, blind, garage, valve)

### M-CON Alarm Issues

**Issue:** Alarm zones not arming/disarming

**Solutions:**
1. Verify Satel integration is configured in M-CON
2. Check zone assignments (Away/Home/Both)
3. Verify alarm panel code if required
4. Check firmware version supports MQTT control

---

## Integration Recovery

### Reload Integration

1. **Settings > Devices & Services > Ampio**
2. Click three-dot menu (⋮)
3. Select **Reload**

### Remove and Re-add

1. **Settings > Devices & Services > Ampio**
2. Click three-dot menu (⋮)
3. Select **Delete**
4. Re-add integration with same credentials

### Clear Entity Registry

If entities are corrupted:

1. Stop Home Assistant
2. Edit `.storage/core.entity_registry`
3. Remove Ampio entries (careful!)
4. Start Home Assistant
5. Re-add integration

---

## Getting Help

### Before Asking for Help

Collect this information:

1. **Home Assistant version**: Settings > About
2. **Ampio integration version**: Check HACS or manifest.json
3. **Ampio MQTT Bridge version**: Check logs or Ampio app
4. **Debug logs**: Enable debug logging, reproduce issue
5. **Diagnostics download**: From integration page
6. **Steps to reproduce**: Detailed description

### Report Issues

1. Check existing issues: https://github.com/mateuszchrobok/ampio-hacc/issues
2. Create new issue with:
   - Clear title
   - Environment details
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs (redact sensitive info)

### Community Resources

- Home Assistant Community: https://community.home-assistant.io/
- Ampio Forum: https://forum.ampio.pl/
- GitHub Discussions: https://github.com/mateuszchrobok/ampio-hacc/discussions
