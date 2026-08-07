"""Base entity for the Pawsync integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Device
from .const import DOMAIN
from .coordinator import PawsyncDataUpdateCoordinator


class PawsyncEntity(CoordinatorEntity[PawsyncDataUpdateCoordinator]):
    """Base entity representing a single Pawsync device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PawsyncDataUpdateCoordinator, device_id: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"

    @property
    def device(self) -> Device:
        """Return the current device data from the coordinator."""
        return self.coordinator.data.devices[self._device_id]

    @property
    def device_info(self) -> DeviceInfo:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return device information."""
        device = self.device
        return DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            name=device.device_name,
            model=device.device_model,
            manufacturer="Pawsync",
            hw_version=device.config_model,
        )
