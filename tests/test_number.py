from unittest.mock import MagicMock

import pytest
from custom_components.pawsync.const import CONF_FEED_FAST_POLL_DURATION
from custom_components.pawsync.number import PawsyncFeedFastPollDurationNumber
from custom_components.pawsync.pawsync import Device

DEVICE_DATA = {
    "deviceName": "Feeder 1",
    "deviceImg": "img_url",
    "deviceDefaultImg": "default_url",
    "deviceId": "id123",
    "connectionType": "wifi",
    "secondaryCategory": "feeder",
    "deviceModel": "model_x",
    "configModel": "config_y",
    "bizId": "biz123",
    "petId": "pet123",
    "deviceProp": {},
}


def _make_number():
    device = Device(DEVICE_DATA)
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.feed_fast_poll_duration = 300
    coordinator.config_entry = MagicMock(options={})

    number = PawsyncFeedFastPollDurationNumber(coordinator, device)
    number.hass = MagicMock()
    number.async_write_ha_state = MagicMock()
    return number, coordinator


def test_native_value_reflects_coordinator_state():
    number, coordinator = _make_number()

    assert number.native_value == 300

    coordinator.feed_fast_poll_duration = 45
    assert number.native_value == 45


@pytest.mark.asyncio
async def test_set_native_value_updates_coordinator_and_options():
    number, coordinator = _make_number()

    await number.async_set_native_value(60)

    assert coordinator.feed_fast_poll_duration == 60
    number.hass.config_entries.async_update_entry.assert_called_once_with(
        coordinator.config_entry,
        options={CONF_FEED_FAST_POLL_DURATION: 60},
    )
    number.async_write_ha_state.assert_called_once()
