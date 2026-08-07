from contextlib import ExitStack

from conftest import USER_INPUT, patch_api
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pawsync.api import PawsyncAuthError
from custom_components.pawsync.const import DOMAIN


async def test_setup_entry_success(hass, loaded_entry):
    assert loaded_entry.state is ConfigEntryState.LOADED
    coordinator = loaded_entry.runtime_data
    assert coordinator.data.devices["id123"].device_name == "Feeder"

    state = hass.states.get("sensor.feeder")
    assert state is not None


async def test_setup_entry_auth_failed(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data=USER_INPUT, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)

    with ExitStack() as stack:
        patch_api(stack, login_side_effect=PawsyncAuthError)
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_unload_entry(hass, loaded_entry):
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert loaded_entry.state is ConfigEntryState.NOT_LOADED
