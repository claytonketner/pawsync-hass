"""Number platform for Pawsync devices."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import pawsync
from .const import CONF_FEED_FAST_POLL_DURATION, DOMAIN, PAWSYNC_COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pawsync number entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][PAWSYNC_COORDINATOR]

    entities = []
    devices = (coordinator.data or {}).get("devices", [])
    for device in devices:
        entities.append(PawsyncFeedFastPollDurationNumber(coordinator, device))

    async_add_entities(entities)


class PawsyncFeedFastPollDurationNumber(CoordinatorEntity, NumberEntity):
    """Number entity to configure how long fast polling stays active after a feed."""

    _attr_icon = "mdi:timer-cog"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = 1
    _attr_native_max_value = 3600
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, device: pawsync.Device):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.device = device
        self._attr_unique_id = f"pawsync_{device.deviceId}_feed_fast_poll_duration"
        self._attr_name = f"{device.deviceName} Feed fast poll duration"

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
    def native_value(self) -> float:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the current fast poll duration."""
        return self.coordinator.feed_fast_poll_duration

    async def async_set_native_value(self, value: float) -> None:
        """Update the fast poll duration."""
        entry = self.coordinator.config_entry
        self.coordinator.feed_fast_poll_duration = int(value)
        self.hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_FEED_FAST_POLL_DURATION: int(value)},
        )
        self.async_write_ha_state()
