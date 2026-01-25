"""MQTT test fixtures and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock

import pytest


@dataclass
class MockMessage:
    """Mock MQTT message for testing."""

    topic: str
    payload: str | bytes
    qos: int = 0
    retain: bool = False
    subscribed_topic: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Set defaults after init."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.subscribed_topic is None:
            self.subscribed_topic = self.topic


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    client = MagicMock()
    client.connected = True
    client.connect = MagicMock(return_value=0)
    client.disconnect = MagicMock()
    client.subscribe = MagicMock(return_value=(0, 1))
    client.unsubscribe = MagicMock(return_value=(0, 1))
    client.publish = MagicMock(return_value=MagicMock(rc=0))
    client.loop_start = MagicMock()
    client.loop_stop = MagicMock()
    return client


@pytest.fixture
def mqtt_message_factory():
    """Factory for creating mock MQTT messages."""

    def _create(
        topic: str,
        payload: str | bytes,
        qos: int = 0,
        retain: bool = False,
        subscribed_topic: str | None = None,
    ) -> MockMessage:
        return MockMessage(
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain,
            subscribed_topic=subscribed_topic,
        )

    return _create


@pytest.fixture
def version_response_payload():
    """Sample version response payload."""
    return '{"version": "3.41.2"}'


@pytest.fixture
def device_list_payload():
    """Sample device list payload from Ampio server."""
    import json

    return json.dumps(
        {
            "s": 1,
            "d": [
                {
                    "mac": "1B88",
                    "user_mac": "AABB",
                    "typ": 44,  # MSENS
                    "pcb": 3,
                    "soft_ver": 100,
                    "protocol": 1,
                    "date_prod": 20230101,
                    "i": 8,
                    "o": 4,
                    "a": 2,
                    "au": 1,
                    "t": 1,
                    "f": 16,
                    "name": "VGVzdCBNb2R1bGU=",  # "Test Module" base64
                },
                {
                    "mac": "1B89",
                    "user_mac": "AABB01",
                    "typ": 5,  # MDIM8s
                    "pcb": 2,
                    "soft_ver": 200,
                    "protocol": 1,
                    "date_prod": 20230201,
                    "i": 0,
                    "o": 8,
                    "a": 0,
                    "au": 0,
                    "t": 0,
                    "f": 8,
                    "name": "RGltbWVyIE1vZHVsZQ==",  # "Dimmer Module" base64
                },
            ],
        }
    )


@pytest.fixture
def description_payload():
    """Sample description/names payload from Ampio server."""
    import json

    return json.dumps(
        {
            "s": 1,
            "d": [
                {
                    "t": "t",
                    "n": 1,
                    "d": "VDpUZW1wZXJhdHVyZQ==",  # "T:Temperature" base64
                },
                {
                    "t": "i",
                    "n": 1,
                    "d": "TTpNb3Rpb24=",  # "M:Motion" base64
                },
                {
                    "t": "o",
                    "n": 1,
                    "d": "TDpMaXZpbmcgUm9vbQ==",  # "L:Living Room" base64
                },
            ],
        }
    )


@pytest.fixture
def sensor_state_payloads():
    """Sample sensor state payloads."""
    return {
        "temperature": "21.5",
        "humidity": "550",  # 55.0% (divided by 10)
        "pressure": "10132",  # 1013.2 hPa (divided by 10)
        "co2": "450",
        "illuminance": "850",
        "noise": "42",
        "air_quality": "75",
    }


@pytest.fixture
def binary_sensor_payloads():
    """Sample binary sensor state payloads."""
    return {
        "on": "1",
        "off": "0",
    }


@pytest.fixture
def switch_payloads():
    """Sample switch state payloads."""
    return {
        "on": "1",
        "off": "0",
    }


@pytest.fixture
def light_payloads():
    """Sample light state payloads."""
    return {
        "brightness_full": "255",
        "brightness_half": "128",
        "brightness_off": "0",
        "rgb_red": "255,0,0",
        "rgb_green": "0,255,0",
        "rgb_blue": "0,0,255",
        "rgb_white": "255,255,255",
        "rgb_off": "0,0,0",
        "rgbw_red": "255,0,0,0",
        "rgbw_white": "0,0,0,255",
    }


@pytest.fixture
def cover_payloads():
    """Sample cover state payloads."""
    return {
        "position_open": "100",
        "position_closed": "0",
        "position_half": "50",
        "tilt_open": "100",
        "tilt_closed": "0",
        "opening": "1",
        "closing": "1",
        "stopped": "0",
    }


@pytest.fixture
def alarm_payloads():
    """Sample alarm state payloads."""
    return {
        "armed": "1",
        "disarmed": "0",
        "alarm_triggered": "1",
        "alarm_clear": "0",
        "entry_time": "1",
        "exit_time": "1",
    }
