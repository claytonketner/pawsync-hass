"""Switch platform for Pawsync devices."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import _apply_polling_interval, pawsync
from .const import DOMAIN, PAWSYNC_COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pawsync switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][PAWSYNC_COORDINATOR]

    entities = []
    devices = (coordinator.data or {}).get("devices", [])
    for device in devices:
        entities.append(PawsyncFastPollingSwitch(coordinator, device))

    async_add_entities(entities)


class PawsyncFastPollingSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to manually force fast polling for a Pawsync device's account."""

    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator, device: pawsync.Device):
        """Initialize the switch."""
        super().__init__(coordinator)
        self.device = device
        self._attr_unique_id = f"pawsync_{device.deviceId}_fast_polling"
        self._attr_name = f"{device.deviceName} Fast polling"

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def device_info(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.device.deviceId)},
            "name": self.device.deviceName,
            "model": self.device.deviceModel,
            "manufacturer": "Pawsync",
            "hw_version": self.device.configModel,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        devices = (self.coordinator.data or {}).get("devices", [])
        for device in devices:
            if device.deviceId == self.device.deviceId:
                self.device = device
                break
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return true if manual fast polling is enabled."""
        return self.coordinator.manual_fast_polling

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable manual fast polling."""
        self.coordinator.manual_fast_polling = True
        _apply_polling_interval(self.coordinator)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable manual fast polling."""
        self.coordinator.manual_fast_polling = False
        _apply_polling_interval(self.coordinator)
        self.async_write_ha_state()
