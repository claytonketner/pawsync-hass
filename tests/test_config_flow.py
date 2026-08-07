from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pawsync.api import PawsyncAuthError
from custom_components.pawsync.const import DOMAIN

USER_INPUT = {"username": "test@example.com", "password": "password123"}


def _patch_login(**kwargs):
    return patch(
        "custom_components.pawsync.config_flow.PawsyncClient.async_login",
        new_callable=AsyncMock,
        **kwargs,
    )


async def test_user_flow_success(hass):
    with _patch_login():
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == USER_INPUT


async def test_user_flow_invalid_auth(hass):
    with _patch_login(side_effect=PawsyncAuthError):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_already_configured(hass):
    MockConfigEntry(
        domain=DOMAIN, unique_id="test@example.com", data=USER_INPUT
    ).add_to_hass(hass)

    with _patch_login():
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_success(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="test@example.com", data=USER_INPUT
    )
    entry.add_to_hass(hass)

    with _patch_login():
        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"password": "new_password"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new_password"


async def test_reauth_flow_invalid_auth(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="test@example.com", data=USER_INPUT
    )
    entry.add_to_hass(hass)

    with _patch_login(side_effect=PawsyncAuthError):
        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"password": "wrong_password"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
