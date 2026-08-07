from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.pawsync.config_flow import PawsyncConfigFlow, PawsyncOptionsFlow
from custom_components.pawsync.const import (
    CONF_FEED_FAST_POLL_DURATION,
    DEFAULT_FEED_FAST_POLL_DURATION,
)


@pytest.mark.asyncio
async def test_config_flow_init():
    flow = PawsyncConfigFlow()
    flow.hass = MagicMock()
    flow.async_show_form = MagicMock(return_value="form_result")

    res = await flow.async_step_user()
    assert res == "form_result"
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_config_flow_user_success():
    flow = PawsyncConfigFlow()
    flow.hass = MagicMock()
    flow.async_create_entry = MagicMock(return_value="entry_result")
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock()

    user_input = {"username": "test@example.com", "password": "password123"}

    with (
        patch(
            "custom_components.pawsync.config_flow.pawsync.login",
            new_callable=AsyncMock,
        ) as mock_login,
        patch(
            "custom_components.pawsync.config_flow.async_get_clientsession"
        ) as mock_get_session,
    ):
        res = await flow.async_step_user(user_input)

        mock_login.assert_called_once_with(
            mock_get_session.return_value, "test@example.com", "password123"
        )
        flow.async_set_unique_id.assert_called_once_with("test@example.com")
        flow.async_create_entry.assert_called_once_with(
            title="test@example.com", data=user_input
        )
        assert res == "entry_result"


def test_config_flow_get_options_flow():
    mock_entry = MagicMock()
    options_flow = PawsyncConfigFlow.async_get_options_flow(mock_entry)
    assert isinstance(options_flow, PawsyncOptionsFlow)


@pytest.mark.asyncio
async def test_options_flow_shows_form_with_default():
    flow = PawsyncOptionsFlow()
    flow.config_entry = MagicMock(options={})
    flow.async_show_form = MagicMock(return_value="form_result")

    # voluptuous is fully mocked in this test harness, so verify the schema
    # is built with the right default rather than inspecting real vol.Schema
    # internals.
    with patch("custom_components.pawsync.config_flow.vol.Required") as mock_required:
        res = await flow.async_step_init()

    assert res == "form_result"
    flow.async_show_form.assert_called_once()
    assert flow.async_show_form.call_args.kwargs["step_id"] == "init"
    mock_required.assert_called_once_with(
        CONF_FEED_FAST_POLL_DURATION, default=DEFAULT_FEED_FAST_POLL_DURATION
    )


@pytest.mark.asyncio
async def test_options_flow_shows_form_with_existing_option():
    flow = PawsyncOptionsFlow()
    flow.config_entry = MagicMock(options={CONF_FEED_FAST_POLL_DURATION: 45})
    flow.async_show_form = MagicMock(return_value="form_result")

    with patch("custom_components.pawsync.config_flow.vol.Required") as mock_required:
        await flow.async_step_init()

    mock_required.assert_called_once_with(CONF_FEED_FAST_POLL_DURATION, default=45)


@pytest.mark.asyncio
async def test_options_flow_saves_input():
    flow = PawsyncOptionsFlow()
    flow.config_entry = MagicMock(options={})
    flow.async_create_entry = MagicMock(return_value="entry_result")

    user_input = {CONF_FEED_FAST_POLL_DURATION: 60}
    res = await flow.async_step_init(user_input)

    assert res == "entry_result"
    flow.async_create_entry.assert_called_once_with(title="", data=user_input)
