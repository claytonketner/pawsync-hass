from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pawsync.api import Device
from custom_components.pawsync.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

USER_INPUT = {"username": "test@example.com", "password": "password123"}

DEVICE_PAYLOAD = {
    "deviceName": "Feeder",
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


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def patch_api(stack: ExitStack, *, login_side_effect=None) -> None:
    """Patch PawsyncClient so tests never touch the network.

    The client's session is never actually used since every PawsyncClient
    method below is mocked, so also avoid HA building a real aiohttp session
    (which would try to open a real socket for DNS resolution).
    """
    stack.enter_context(
        patch(
            "custom_components.pawsync.async_get_clientsession",
            return_value=MagicMock(),
        )
    )
    stack.enter_context(
        patch(
            "custom_components.pawsync.api.PawsyncClient.async_login",
            new_callable=AsyncMock,
            side_effect=login_side_effect,
        )
    )
    stack.enter_context(
        patch(
            "custom_components.pawsync.api.PawsyncClient.async_get_device_list",
            new_callable=AsyncMock,
            return_value=[Device.from_api(DEVICE_PAYLOAD)],
        )
    )
    stack.enter_context(
        patch(
            "custom_components.pawsync.api.PawsyncClient.async_get_status",
            new_callable=AsyncMock,
            return_value={},
        )
    )
    stack.enter_context(
        patch(
            "custom_components.pawsync.api.PawsyncClient.async_get_pet_log_list",
            new_callable=AsyncMock,
            return_value=[],
        )
    )


@pytest.fixture
async def loaded_entry(hass) -> MockConfigEntry:
    """Set up a Pawsync config entry with a mocked API client."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=USER_INPUT, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)

    with ExitStack() as stack:
        patch_api(stack)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry
