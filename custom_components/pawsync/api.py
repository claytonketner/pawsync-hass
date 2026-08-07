"""Pawsync cloud API client."""

from __future__ import annotations

import hashlib
import logging
import random
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://smartapi.pawsync.com/pet/api"
TOKEN_INVALID_CODE = -11008800  # Pawsync API code when the auth token has expired


class PawsyncApiError(Exception):
    """Raised when the Pawsync API returns an error."""


class PawsyncAuthError(PawsyncApiError):
    """Raised when authentication fails or the session token has expired."""


@dataclass
class Device:
    """A Pawsync device."""

    device_id: str
    device_name: str
    device_img: str
    device_default_img: str
    connection_type: str
    secondary_category: str
    device_model: str
    config_model: str
    biz_id: str
    pet_id: str
    device_prop: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Device:
        """Build a Device from a Pawsync deviceList4Pet API entry."""
        return cls(
            device_id=data["deviceId"],
            device_name=data["deviceName"],
            device_img=data["deviceImg"],
            device_default_img=data["deviceDefaultImg"],
            connection_type=data["connectionType"],
            secondary_category=data["secondaryCategory"],
            device_model=data["deviceModel"],
            config_model=data["configModel"],
            biz_id=data["bizId"],
            pet_id=data["petId"],
            device_prop=data["deviceProp"],
        )


class PawsyncClient:
    """Client for the Pawsync cloud API.

    Holds the account's auth token and terminal/trace identifiers, so each
    Home Assistant config entry (Pawsync account) must use its own instance.
    """

    def __init__(
        self, session: aiohttp.ClientSession, email: str, password: str
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._terminal_id = hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]
        trace_uuid = str(uuid.uuid4()).replace("-", "")
        self._trace_id = f"PET{trace_uuid[-16:]}-{random.randint(0, 99999):05}"
        self._account_id: str | None = None
        self._token: str | None = None

    def _context(self, method: str) -> dict[str, Any]:
        return {
            "acceptLanguage": "en",
            "accountID": self._account_id,
            "appID": "psybfyca",
            "clientInfo": "API",
            "clientType": "pawsync",
            "clientVersion": "Pawsync 1.0.85",
            "debugMode": "false",
            "method": method,
            "osInfo": "Android 15",
            "terminalId": self._terminal_id,
            "timeZone": "America/Los_Angeles",
            "token": self._token,
            "traceId": self._trace_id,
            "userCountryCode": "US",
        }

    async def _post(
        self, type_: str, method: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {"context": self._context(method), "data": data}
        response = await self._session.post(
            f"{API_BASE_URL}/{type_}/v1/{method}", json=payload
        )
        return await response.json()

    async def async_login(self) -> None:
        """Authenticate and store the session token."""
        result = await self._post(
            "userManaged",
            "login",
            {
                "email": self._email,
                "password": hashlib.sha256(self._password.encode("utf-8")).hexdigest(),
            },
        )
        if result.get("code") != 0 or result.get("result") is None:
            _LOGGER.error("Pawsync login failed: %s", result)
            raise PawsyncAuthError("Pawsync login failed")

        self._account_id = result["result"]["accountId"]
        self._token = result["result"]["token"]

    async def _post_bypass(
        self, device: Device, method: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a device command via the bypassV2 envelope."""
        ctx = self._context("bypassV2")
        payload = {
            "acceptLanguage": ctx["acceptLanguage"],
            "accountID": ctx["accountID"],
            "appID": ctx["appID"],
            "appVersion": ctx["clientVersion"],
            "debugMode": ctx["debugMode"],
            "method": "bypassV2",
            "phoneBrand": "",
            "phoneOS": ctx["osInfo"],
            "timeZone": ctx["timeZone"],
            "token": ctx["token"],
            "traceId": ctx["traceId"],
            "userCountryCode": ctx["userCountryCode"],
            "cid": device.device_id,
            "configModule": device.config_model,
            "payload": {
                "data": {
                    **(data or {}),
                    "cid": device.device_id,
                    "configModule": device.config_model,
                },
                "method": method,
                "source": "APP",
            },
        }
        response = await self._session.post(
            f"{API_BASE_URL}/deviceManaged/v1/bypassV2", json=payload
        )
        result = await response.json()
        if result.get("code") == TOKEN_INVALID_CODE:
            raise PawsyncAuthError("Pawsync session token expired")
        return result

    async def async_request_feed(self, device: Device, amount: int) -> None:
        """Request a manual feed for a device."""
        _LOGGER.debug(
            "Requesting feed for device %s, amount=%s", device.device_id, amount
        )
        result = await self._post_bypass(device, "manualFeeding", {"serving1": amount})
        if result.get("code") != 0:
            raise PawsyncApiError(
                f"Feed request failed for {device.device_id}: {result}"
            )

    async def async_get_status(self, device: Device) -> dict[str, Any]:
        """Fetch real-time device state via getPetDeviceStatus."""
        result = await self._post_bypass(device, "getPetDeviceStatus")
        if result.get("code") != 0:
            raise PawsyncApiError(
                f"getPetDeviceStatus failed for {device.device_id}: {result}"
            )
        inner = result.get("result") or {}
        if inner.get("code") != 0:
            raise PawsyncApiError(
                f"getPetDeviceStatus inner error for {device.device_id}: {inner}"
            )
        return inner.get("result") or {}

    async def async_get_device_list(self) -> list[Device]:
        """Fetch the account's devices."""
        result = await self._post("deviceManaged", "deviceList4Pet", {})
        if result.get("code") == TOKEN_INVALID_CODE:
            raise PawsyncAuthError("Pawsync session token expired")
        if result.get("code") != 0 or result.get("result") is None:
            raise PawsyncApiError(f"getDeviceList failed: {result}")
        return [Device.from_api(d) for d in result["result"]["list"]]

    async def async_get_pet_log_list(
        self, device_id: str, page_size: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch feeding activity logs for the last 24 hours."""
        end_ts = int(time.time())
        start_ts = end_ts - 86400
        result = await self._post(
            "petDeviceManaged",
            "getPetLogList",
            {
                "deviceId": device_id,
                "endTimestamp": end_ts,
                "objectType": 0,
                "pageSize": page_size,
                "startTimestamp": start_ts,
            },
        )
        if result.get("code") == TOKEN_INVALID_CODE:
            raise PawsyncAuthError("Pawsync session token expired")
        if result.get("code") != 0 or result.get("result") is None:
            raise PawsyncApiError(f"getPetLogList failed for {device_id}: {result}")
        return result["result"].get("petLogList", [])
