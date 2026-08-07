from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.pawsync.api import Device, PawsyncApiError, PawsyncAuthError
from custom_components.pawsync.const import DOMAIN
from custom_components.pawsync.coordinator import PawsyncData
from custom_components.pawsync.sensor import (
    LOG_SENSOR_TYPES,
    SENSOR_TYPES,
    PawsyncDeviceSensor,
    PawsyncLogSensor,
)

DEVICE_ID = "id123"


def make_device(device_prop):
    return Device(
        device_id=DEVICE_ID,
        device_name="Feeder 1",
        device_img="img_url",
        device_default_img="default_url",
        connection_type="wifi",
        secondary_category="feeder",
        device_model="model_x",
        config_model="config_y",
        biz_id="biz123",
        pet_id="pet123",
        device_prop=device_prop,
    )


def make_coordinator(device, pet_logs=None):
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = PawsyncData(
        devices={DEVICE_ID: device}, pet_logs={DEVICE_ID: pet_logs or []}
    )
    return coordinator


def test_sensors():
    device = make_device(
        {
            "connectionStatus": "online",
            "contentInPot": 250,
            "bowlWeight": 5,
            "petFood": {
                "bucketSurplus": 1500,
                "lastFeedingAmount": 12,
                "contentRemainTime": 5,
            },
            "batteryPercent": 85,
            "wifiRssi": -60,
            "alertCount": 0,
            "firmwareInfos": [
                {"version": "1.0.85", "isMainFw": True},
                {"version": "mcu_1.0", "pluginName": "mcuFw"},
            ],
        }
    )
    coordinator = make_coordinator(device)

    sensors = [
        PawsyncDeviceSensor(coordinator, DEVICE_ID, desc) for desc in SENSOR_TYPES
    ]

    assert sensors[0].native_value == "online"
    assert sensors[1].native_value == 250
    assert sensors[2].native_value == 5
    assert sensors[3].native_value == 1500
    assert sensors[4].native_value == 12
    assert sensors[5].native_value == 5
    assert sensors[6].native_value == 85
    assert sensors[7].native_value == -60
    assert sensors[8].native_value == 0
    assert sensors[9].native_value == "1.0.85"
    assert sensors[10].native_value == "mcu_1.0"

    assert sensors[0].device_info["identifiers"] == {(DOMAIN, DEVICE_ID)}
    assert sensors[0].unique_id == f"{DEVICE_ID}_primary"

    assert sensors[0].available is True
    coordinator.last_update_success = False
    assert sensors[0].available is False


def test_log_sensors():
    device = make_device({})
    logs = [
        {"timestamp": 1713600000, "logType": "planFeeding", "value": 11},
        {
            "timestamp": 1713610000,
            "logType": "takeFood",
            "value": 8,
            "durationInS": 120,
        },
    ]
    coordinator = make_coordinator(device, logs)

    sensors = [
        PawsyncLogSensor(coordinator, DEVICE_ID, desc) for desc in LOG_SENSOR_TYPES
    ]

    assert sensors[0].native_value == datetime.fromtimestamp(1713600000, tz=UTC)
    assert sensors[1].native_value == 11
    assert sensors[2].native_value == datetime.fromtimestamp(1713610000, tz=UTC)
    assert sensors[3].native_value == 8
    assert sensors[4].native_value == 120


async def test_request_feed_success():
    device = make_device({})
    coordinator = make_coordinator(device)
    coordinator.client.async_request_feed = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()

    sensor = PawsyncDeviceSensor(coordinator, DEVICE_ID, SENSOR_TYPES[0])
    await sensor.async_request_feed(15)

    coordinator.client.async_request_feed.assert_called_once_with(device, 15)
    coordinator.request_fast_poll.assert_called_once()
    coordinator.async_request_refresh.assert_called_once()


async def test_request_feed_reauthenticates_on_expired_token():
    device = make_device({})
    coordinator = make_coordinator(device)
    coordinator.client.async_request_feed = AsyncMock(
        side_effect=[PawsyncAuthError, None]
    )
    coordinator.client.async_login = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()

    sensor = PawsyncDeviceSensor(coordinator, DEVICE_ID, SENSOR_TYPES[0])
    await sensor.async_request_feed(15)

    coordinator.client.async_login.assert_called_once()
    assert coordinator.client.async_request_feed.call_count == 2


async def test_request_feed_api_error_raises_home_assistant_error():
    device = make_device({})
    coordinator = make_coordinator(device)
    coordinator.client.async_request_feed = AsyncMock(side_effect=PawsyncApiError)

    sensor = PawsyncDeviceSensor(coordinator, DEVICE_ID, SENSOR_TYPES[0])

    with pytest.raises(HomeAssistantError):
        await sensor.async_request_feed(15)
