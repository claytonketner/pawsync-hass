import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.pawsync.api import (
    TOKEN_INVALID_CODE,
    Device,
    PawsyncApiError,
    PawsyncAuthError,
    PawsyncClient,
)

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
    "deviceProp": {"level": 100},
}


def make_session(json_result):
    session = MagicMock()
    response = MagicMock()
    response.json = AsyncMock(return_value=json_result)
    session.post = AsyncMock(return_value=response)
    return session


def test_device_from_api():
    device = Device.from_api(DEVICE_PAYLOAD)
    assert device.device_name == "Feeder"
    assert device.device_id == "id123"
    assert device.device_prop == {"level": 100}


async def test_login_success():
    session = make_session(
        {"code": 0, "result": {"accountId": "acc_123", "token": "token_abc"}}
    )
    client = PawsyncClient(session, "test@example.com", "password123")

    await client.async_login()

    assert client._account_id == "acc_123"
    assert client._token == "token_abc"


async def test_login_failed_raises_auth_error():
    session = make_session({"code": 1, "result": None})
    client = PawsyncClient(session, "test@example.com", "password123")

    with pytest.raises(PawsyncAuthError):
        await client.async_login()


def test_terminal_id_derived_from_email():
    session = make_session({})
    client = PawsyncClient(session, "test@example.com", "password123")

    expected = hashlib.sha256(b"test@example.com").hexdigest()[:32]
    assert client._terminal_id == expected


async def test_get_device_list_success():
    session = make_session({"code": 0, "result": {"list": [DEVICE_PAYLOAD]}})
    client = PawsyncClient(session, "test@example.com", "password123")

    devices = await client.async_get_device_list()

    assert len(devices) == 1
    assert devices[0].device_name == "Feeder"
    assert devices[0].device_id == "id123"


async def test_get_device_list_failed_raises_api_error():
    session = make_session({"code": -1, "result": None})
    client = PawsyncClient(session, "test@example.com", "password123")

    with pytest.raises(PawsyncApiError):
        await client.async_get_device_list()


async def test_get_device_list_token_invalid_raises_auth_error():
    session = make_session({"code": TOKEN_INVALID_CODE, "result": None})
    client = PawsyncClient(session, "test@example.com", "password123")

    with pytest.raises(PawsyncAuthError):
        await client.async_get_device_list()


async def test_request_feed_success():
    session = make_session({"code": 0})
    client = PawsyncClient(session, "test@example.com", "password123")
    device = Device.from_api(DEVICE_PAYLOAD)

    await client.async_request_feed(device, 15)

    session.post.assert_called_once()


async def test_request_feed_token_invalid_raises_auth_error():
    session = make_session({"code": TOKEN_INVALID_CODE})
    client = PawsyncClient(session, "test@example.com", "password123")
    device = Device.from_api(DEVICE_PAYLOAD)

    with pytest.raises(PawsyncAuthError):
        await client.async_request_feed(device, 15)


async def test_get_status_success():
    session = make_session(
        {
            "code": 0,
            "result": {
                "code": 0,
                "result": {"bowlWeight": 10, "desiccantRemainTime": 30},
            },
        }
    )
    client = PawsyncClient(session, "test@example.com", "password123")
    device = Device.from_api(DEVICE_PAYLOAD)

    status = await client.async_get_status(device)

    assert status == {"bowlWeight": 10, "desiccantRemainTime": 30}


async def test_get_status_failed_raises_api_error():
    session = make_session({"code": -1})
    client = PawsyncClient(session, "test@example.com", "password123")
    device = Device.from_api(DEVICE_PAYLOAD)

    with pytest.raises(PawsyncApiError):
        await client.async_get_status(device)


async def test_get_pet_log_list_success():
    session = make_session(
        {
            "code": 0,
            "result": {
                "petLogList": [
                    {"timestamp": 1234567890, "logType": "planFeeding", "value": 11}
                ]
            },
        }
    )
    client = PawsyncClient(session, "test@example.com", "password123")

    logs = await client.async_get_pet_log_list("device_123")

    assert len(logs) == 1
    assert logs[0]["logType"] == "planFeeding"
    assert logs[0]["value"] == 11


async def test_get_pet_log_list_failed_raises_api_error():
    session = make_session({"code": -1, "result": None})
    client = PawsyncClient(session, "test@example.com", "password123")

    with pytest.raises(PawsyncApiError):
        await client.async_get_pet_log_list("device_123")
