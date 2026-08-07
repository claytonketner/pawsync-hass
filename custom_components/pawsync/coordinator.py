"""Data update coordinator for the Pawsync integration."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Device, PawsyncApiError, PawsyncAuthError, PawsyncClient
from .const import FAST_POLL_INTERVAL, FEED_FAST_POLL_DURATION, NORMAL_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

type PawsyncConfigEntry = ConfigEntry[PawsyncDataUpdateCoordinator]


@dataclass
class PawsyncData:
    """Data fetched on each coordinator update."""

    devices: dict[str, Device] = field(default_factory=dict)
    pet_logs: dict[str, list] = field(default_factory=dict)


class PawsyncDataUpdateCoordinator(DataUpdateCoordinator[PawsyncData]):
    """Coordinates polling the Pawsync API for a single account."""

    config_entry: PawsyncConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: PawsyncConfigEntry, client: PawsyncClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="pawsync",
            update_interval=NORMAL_POLL_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        self.manual_fast_polling = False
        self._feed_fast_polling_until: float | None = None

    def request_fast_poll(self) -> None:
        """Switch to fast polling for a limited time after a feed request."""
        self._feed_fast_polling_until = (
            time.time() + FEED_FAST_POLL_DURATION.total_seconds()
        )
        self._apply_polling_interval()

    def _apply_polling_interval(self) -> None:
        """Recompute the update interval from all fast-poll triggers.

        Two independent triggers can request fast polling: a feed request
        (time-limited, tracked by _feed_fast_polling_until) and the manual
        fast-polling switch. Each trigger only touches its own flag, so the
        effective interval is recomputed from both rather than one trigger
        clobbering the other's state.
        """
        if (
            self._feed_fast_polling_until is not None
            and time.time() > self._feed_fast_polling_until
        ):
            self._feed_fast_polling_until = None

        if self._feed_fast_polling_until is not None or self.manual_fast_polling:
            self.update_interval = FAST_POLL_INTERVAL
        else:
            self.update_interval = NORMAL_POLL_INTERVAL

    async def _async_update_data(self) -> PawsyncData:
        self._apply_polling_interval()

        try:
            devices = await self.client.async_get_device_list()
        except PawsyncAuthError:
            await self._async_reauthenticate()
            devices = await self.client.async_get_device_list()
        except PawsyncApiError as err:
            raise UpdateFailed(f"Error communicating with Pawsync: {err}") from err

        pawsync_data = PawsyncData()
        for device in devices:
            try:
                status = await self.client.async_get_status(device)
            except PawsyncApiError as err:
                _LOGGER.warning(
                    "Could not fetch status for device %s: %s", device.device_id, err
                )
            else:
                device.device_prop.update(status)
            pawsync_data.devices[device.device_id] = device

            try:
                pawsync_data.pet_logs[
                    device.device_id
                ] = await self.client.async_get_pet_log_list(device.device_id)
            except PawsyncApiError as err:
                _LOGGER.warning(
                    "Could not fetch pet logs for device %s: %s",
                    device.device_id,
                    err,
                )
                pawsync_data.pet_logs[device.device_id] = []

        return pawsync_data

    async def _async_reauthenticate(self) -> None:
        try:
            await self.client.async_login()
        except PawsyncAuthError as err:
            raise ConfigEntryAuthFailed(
                "Pawsync credentials are no longer valid"
            ) from err
