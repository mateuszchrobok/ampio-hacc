# Testing Guide

This guide covers how to run existing tests and write new tests for the Ampio integration.

## Prerequisites

### Install Development Dependencies

```bash
# Using pip
pip install -e ".[dev]"

# Using uv (recommended)
uv pip install -e ".[dev]"
```

This installs:
- pytest
- pytest-cov
- ruff (linting)
- mypy (type checking)

## Running Tests

### Run All Tests

```bash
# Basic run
pytest tests/ -v

# With uv
uv run pytest tests/ -v
```

### Run Specific Test Files

```bash
# Test models only
pytest tests/test_models.py -v

# Test validators only
pytest tests/test_validators.py -v
```

### Run Specific Tests

```bash
# Run test by name
pytest tests/test_models.py::test_item_name_parsing -v

# Run tests matching pattern
pytest tests/ -k "test_device_class" -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/ -v --cov=custom_components.ampio

# Generate HTML coverage report
pytest tests/ -v --cov=custom_components.ampio --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Run with Verbose Output

```bash
# Show print statements
pytest tests/ -v -s

# Show full diff on failures
pytest tests/ -v --tb=long
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures, HA mocks
├── fixtures/
│   ├── __init__.py
│   └── mqtt.py              # MQTT-specific fixtures
├── test_const.py            # Constants tests
├── test_models.py           # Model class tests
├── test_validators.py       # Validator tests
└── test_mixins.py           # Mixin tests
```

## Fixtures

### Core Fixtures (conftest.py)

#### sample_device_payload

Complete device discovery payload:

```python
def test_device_discovery(sample_device_payload):
    """Test device discovery parsing."""
    modules = AmpioModuleInfo.from_topic_payload(sample_device_payload)
    assert len(modules) == 1
    assert modules[0].user_mac == "AABB"
```

#### sample_description_payload

Module item names payload:

```python
def test_description_parsing(sample_description_payload):
    """Test description/names parsing."""
    names = ItemName.from_topic_payload(sample_description_payload)
    assert "t" in names
    assert names["t"][1].name == "Temperature"
```

### MQTT Fixtures (fixtures/mqtt.py)

#### mock_mqtt_client

Pre-configured mock MQTT client:

```python
def test_mqtt_publish(mock_mqtt_client):
    """Test MQTT publishing."""
    mock_mqtt_client.publish("ampio/to/AABB/o/1/cmd", "1")
    mock_mqtt_client.publish.assert_called_once()
```

#### mqtt_message_factory

Factory for creating test messages:

```python
def test_message_handling(mqtt_message_factory):
    """Test message handling."""
    msg = mqtt_message_factory(
        topic="ampio/from/AABB/state/t/1",
        payload="21.5"
    )
    assert msg.topic == "ampio/from/AABB/state/t/1"
    assert msg.payload == "21.5"
```

#### sensor_state_payloads

Sample sensor values:

```python
def test_temperature_parsing(sensor_state_payloads):
    """Test temperature value parsing."""
    temp = float(sensor_state_payloads["temperature"])
    assert temp == 21.5
```

#### cover_payloads / light_payloads / alarm_payloads

Platform-specific test data:

```python
def test_cover_position(cover_payloads):
    """Test cover position parsing."""
    assert int(cover_payloads["position_open"]) == 100
    assert int(cover_payloads["position_closed"]) == 0
```

## Writing Tests

### Basic Test Structure

```python
"""Tests for my feature."""

import pytest

from custom_components.ampio.models import AmpioModuleInfo


def test_feature_basic():
    """Test basic feature functionality."""
    # Arrange
    input_data = {"key": "value"}

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected_value


def test_feature_edge_case():
    """Test edge case handling."""
    with pytest.raises(ValueError):
        my_function(None)


class TestMyClass:
    """Tests for MyClass."""

    def test_initialization(self):
        """Test class initialization."""
        obj = MyClass()
        assert obj.value is None

    def test_method(self):
        """Test specific method."""
        obj = MyClass()
        obj.set_value(42)
        assert obj.value == 42
```

### Using Fixtures

```python
def test_with_fixture(sample_device_payload):
    """Test using a fixture."""
    # Fixture is automatically injected
    assert "d" in sample_device_payload
    assert len(sample_device_payload["d"]) == 1


def test_with_multiple_fixtures(mock_mqtt_client, mqtt_message_factory):
    """Test using multiple fixtures."""
    msg = mqtt_message_factory("topic", "payload")
    mock_mqtt_client.publish(msg.topic, msg.payload)
    mock_mqtt_client.publish.assert_called_with("topic", "payload")
```

### Creating Custom Fixtures

```python
@pytest.fixture
def my_custom_fixture():
    """Create custom test data."""
    return {
        "unique_id": "ampio-TEST-t1",
        "name": "Test Sensor",
        "state_topic": "ampio/from/TEST/state/t/1",
    }


def test_with_custom_fixture(my_custom_fixture):
    """Use custom fixture in test."""
    assert my_custom_fixture["unique_id"] == "ampio-TEST-t1"
```

### Parametrized Tests

```python
@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("21.5", 21.5),
        ("0", 0.0),
        ("-5.5", -5.5),
        ("100", 100.0),
    ],
)
def test_temperature_parsing(input_value, expected):
    """Test temperature parsing with various values."""
    result = parse_temperature(input_value)
    assert result == expected


@pytest.mark.parametrize(
    "prefix,device_class",
    [
        ("T:", "temperature"),
        ("M:", "motion"),
        ("D:", "door"),
        ("W:", "window"),
        ("L:", "light"),
        ("", None),  # No prefix
    ],
)
def test_device_class_extraction(prefix, device_class):
    """Test device class extraction from name prefix."""
    import base64
    name = base64.b64encode(f"{prefix}Test".encode()).decode()
    item = ItemName(name)
    assert item.device_class == device_class
```

### Mocking

```python
from unittest.mock import MagicMock, patch, AsyncMock


def test_with_mock():
    """Test with mocked dependency."""
    with patch("custom_components.ampio.coordinator.AmpioMQTTClient") as mock_client:
        mock_client.return_value.connected = True
        # Test code that uses MQTT client


def test_async_mock():
    """Test async code with mock."""
    mock_coordinator = MagicMock()
    mock_coordinator.async_publish = AsyncMock()

    # Can await the mock
    # await mock_coordinator.async_publish("topic", "payload")


def test_callback_mock(mock_mqtt_client):
    """Test callback invocation."""
    callback = MagicMock()
    mock_mqtt_client.on_message = callback

    # Simulate message
    mock_mqtt_client.on_message(None, None, MockMessage("topic", "payload"))

    callback.assert_called_once()
```

### Testing Entity Classes

```python
def test_entity_creation():
    """Test entity initialization."""
    config = {
        "unique_id": "ampio-AABB-t1",
        "name": "ampio-AABB-t1",
        "friendly_name": "Temperature",
        "state_topic": "ampio/from/AABB/state/t/1",
        "device_class": "temperature",
    }

    entity = AmpioSensorEntity(config)

    assert entity.unique_id == "ampio-AABB-t1"
    assert entity.device_class == "temperature"


def test_entity_state_update(mqtt_message_factory):
    """Test entity state update."""
    config = {
        "unique_id": "ampio-AABB-t1",
        "state_topic": "ampio/from/AABB/state/t/1",
    }
    entity = AmpioSensorEntity(config)

    msg = mqtt_message_factory(
        topic="ampio/from/AABB/state/t/1",
        payload="21.5"
    )

    entity._handle_state_message(msg)

    assert entity.native_value == 21.5
```

### Testing Model Classes

```python
def test_module_info_creation(sample_device_payload):
    """Test AmpioModuleInfo creation from payload."""
    modules = AmpioModuleInfo.from_topic_payload(sample_device_payload)

    assert len(modules) == 1
    module = modules[0]

    assert module.mac == "1B88"
    assert module.user_mac == "AABB"
    assert module.code == 44
    assert module.name == "Test Module"


def test_item_name_parsing():
    """Test ItemName parsing."""
    # "T:Kitchen" in base64
    import base64
    encoded = base64.b64encode("T:Kitchen".encode()).decode()

    item = ItemName(encoded)

    assert item.name == "Kitchen"
    assert item.prefix == "T"
    assert item.device_class == "temperature"


def test_entity_config_generation(sample_device_payload, sample_description_payload):
    """Test entity config generation."""
    modules = AmpioModuleInfo.from_topic_payload(sample_device_payload)
    module = modules[0]

    names = ItemName.from_topic_payload(sample_description_payload)
    module.names = names
    module.update_configs()

    # Check sensor configs were created
    assert "sensor" in module.configs
    assert len(module.configs["sensor"]) > 0
```

## Code Quality Checks

### Linting with Ruff

```bash
# Check for issues
ruff check custom_components/ampio

# Auto-fix issues
ruff check custom_components/ampio --fix

# Check specific rules
ruff check custom_components/ampio --select E,W
```

### Type Checking with MyPy

```bash
# Run mypy
mypy custom_components/ampio

# Ignore missing imports (common for HA)
mypy custom_components/ampio --ignore-missing-imports
```

### Formatting

```bash
# Check formatting
ruff format --check custom_components/ampio

# Apply formatting
ruff format custom_components/ampio
```

## CI/CD

The project uses GitHub Actions for continuous integration. See `.github/workflows/ci.yaml`.

Tests are run automatically on:
- Push to main branch
- Pull requests

### Running CI Locally

```bash
# Simulate CI environment
pip install -e ".[dev]"
ruff check custom_components/ampio
pytest tests/ -v
```

## Troubleshooting Tests

### Import Errors

If you see import errors:

1. Check `conftest.py` has all required HA mocks
2. Ensure test runs from project root directory
3. Verify development dependencies are installed

### Mock Issues

If mocks don't work:

```python
# Verify mock is being used
def test_with_mock():
    with patch("custom_components.ampio.module.function") as mock:
        mock.return_value = "test"
        # Use full module path where function is USED, not DEFINED
```

### Async Test Issues

For async tests:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result == expected
```

### Coverage Gaps

To find untested code:

```bash
# Generate detailed coverage
pytest tests/ -v --cov=custom_components.ampio --cov-report=term-missing

# View per-file coverage
pytest tests/ -v --cov=custom_components.ampio --cov-report=html
```

## Best Practices

1. **Test one thing per test** - Keep tests focused
2. **Use descriptive names** - `test_temperature_sensor_returns_float`
3. **Use fixtures** - Share common test data
4. **Parametrize** - Test multiple inputs efficiently
5. **Mock external dependencies** - Don't rely on real MQTT
6. **Test edge cases** - Empty data, None, invalid values
7. **Keep tests fast** - No network calls, no sleep
8. **Run tests before committing** - `pytest tests/ -v`
