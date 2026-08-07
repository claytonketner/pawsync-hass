import time
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.pawsync import FAST_POLL_INTERVAL, NORMAL_POLL_INTERVAL
from custom_components.pawsync.pawsync import Device
from custom_components.pawsync.switch import PawsyncFastPollingSwitch

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


def _make_switch():
    device = Device(DEVICE_DATA)
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.manual_fast_polling = False
    coordinator.feed_fast_polling_until = None
    coordinator.async_request_refresh = AsyncMock()

    switch = PawsyncFastPollingSwitch(coordinator, device)
    switch.async_write_ha_state = MagicMock()
    return switch, coordinator


def test_is_on_reflects_coordinator_state():
    switch, coordinator = _make_switch()

    assert switch.is_on is False

    coordinator.manual_fast_polling = True
    assert switch.is_on is True


@pytest.mark.asyncio
async def test_turn_on_enables_manual_fast_polling():
    switch, coordinator = _make_switch()

    await switch.async_turn_on()

    assert coordinator.manual_fast_polling is True
    assert coordinator.update_interval == FAST_POLL_INTERVAL
    switch.async_write_ha_state.assert_called_once()
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_turn_off_disables_manual_fast_polling():
    switch, coordinator = _make_switch()
    coordinator.manual_fast_polling = True

    await switch.async_turn_off()

    assert coordinator.manual_fast_polling is False
    assert coordinator.update_interval == NORMAL_POLL_INTERVAL
    switch.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_turn_off_keeps_fast_polling_if_feed_trigger_still_active():
    switch, coordinator = _make_switch()
    coordinator.manual_fast_polling = True
    coordinator.feed_fast_polling_until = time.time() + 20

    await switch.async_turn_off()

    assert coordinator.manual_fast_polling is False
    assert coordinator.update_interval == timedelta(seconds=15)
