"""Binary sensor platform for Pawsync devices."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import Device
from .coordinator import PawsyncConfigEntry, PawsyncDataUpdateCoordinator
from .entity import PawsyncEntity


@dataclass(frozen=True, kw_only=True)
class PawsyncBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing Pawsync binary sensor entities."""

    value_fn: Callable[[Device], Any] | None = None


BINARY_SENSOR_TYPES: tuple[PawsyncBinarySensorEntityDescription, ...] = (
    PawsyncBinarySensorEntityDescription(
        key="power_adapter",
        translation_key="power_adapter",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda device: device.device_prop.get("powerAdapter") == 1,
    ),
    PawsyncBinarySensorEntityDescription(
        key="intelligent_feeding",
        translation_key="intelligent_feeding",
        icon="mdi:robot-pet",
        value_fn=lambda device: device.device_prop.get("intelligentFeedingSwitch") == 1,
    ),
    PawsyncBinarySensorEntityDescription(
        key="slow_feed",
        translation_key="slow_feed",
        icon="mdi:speedometer-slow",
        value_fn=lambda device: device.device_prop.get("slowFeedSwitch") == 1,
    ),
    PawsyncBinarySensorEntityDescription(
        key="accurate_feeding",
        translation_key="accurate_feeding",
        icon="mdi:target",
        value_fn=lambda device: device.device_prop.get("accurateFeeding") == 1,
    ),
    PawsyncBinarySensorEntityDescription(
        key="bowl_missing",
        translation_key="bowl_missing",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: (
            device.device_prop.get("bowlConnected") != "normal"
            if device.device_prop.get("bowlConnected") is not None
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PawsyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pawsync binary sensor entities from a config entry."""
    coordinator = entry.runtime_data

    entities = [
        PawsyncDeviceBinarySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in BINARY_SENSOR_TYPES
    ]

    async_add_entities(entities)


class PawsyncDeviceBinarySensor(PawsyncEntity, BinarySensorEntity):
    """Representation of a Pawsync device binary sensor."""

    entity_description: PawsyncBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: PawsyncDataUpdateCoordinator,
        device_id: str,
        description: PawsyncBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return true if the binary sensor is on."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.device)
        return None
