from unittest.mock import MagicMock

from custom_components.pawsync.api import Device
from custom_components.pawsync.binary_sensor import (
    BINARY_SENSOR_TYPES,
    PawsyncDeviceBinarySensor,
)
from custom_components.pawsync.const import DOMAIN
from custom_components.pawsync.coordinator import PawsyncData

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


def test_binary_sensors():
    device = make_device(
        {
            "powerAdapter": 1,
            "intelligentFeedingSwitch": 0,
            "slowFeedSwitch": 1,
            "accurateFeeding": 0,
            "bowlConnected": "normal",
        }
    )
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = PawsyncData(devices={DEVICE_ID: device})

    sensors = [
        PawsyncDeviceBinarySensor(coordinator, DEVICE_ID, desc)
        for desc in BINARY_SENSOR_TYPES
    ]

    assert sensors[0].is_on is True
    assert sensors[1].is_on is False
    assert sensors[2].is_on is True
    assert sensors[3].is_on is False
    assert sensors[4].is_on is False

    assert sensors[0].device_info["identifiers"] == {(DOMAIN, DEVICE_ID)}
    assert sensors[0].unique_id == f"{DEVICE_ID}_power_adapter"


def test_bowl_missing_unknown_when_not_reported():
    device = make_device({})
    coordinator = MagicMock()
    coordinator.data = PawsyncData(devices={DEVICE_ID: device})

    sensor = PawsyncDeviceBinarySensor(coordinator, DEVICE_ID, BINARY_SENSOR_TYPES[4])

    assert sensor.is_on is None
