"""Test fixtures for ampio-hacc."""

import pytest


@pytest.fixture
def sample_device_payload():
    """Sample device list payload from Ampio server."""
    return {
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
            }
        ],
    }


@pytest.fixture
def sample_description_payload():
    """Sample description payload from Ampio server."""
    return {
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
        ],
    }
