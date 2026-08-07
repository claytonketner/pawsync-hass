"""Sensor platform for Pawsync devices."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import Device, PawsyncApiError, PawsyncAuthError
from .coordinator import PawsyncConfigEntry, PawsyncDataUpdateCoordinator
from .entity import PawsyncEntity
from .services import async_register_entity_services


@dataclass(frozen=True, kw_only=True)
class PawsyncSensorEntityDescription(SensorEntityDescription):
    """Class describing Pawsync sensor entities."""

    value_fn: Callable[[Device], Any] | None = None


SENSOR_TYPES: tuple[PawsyncSensorEntityDescription, ...] = (
    PawsyncSensorEntityDescription(
        key="primary",
        value_fn=lambda device: device.device_prop.get("connectionStatus"),
    ),
    PawsyncSensorEntityDescription(
        key="content_in_pot",
        translation_key="content_in_pot",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:bowl-mix",
        value_fn=lambda device: device.device_prop.get("contentInPot"),
    ),
    PawsyncSensorEntityDescription(
        key="bowl_weight",
        translation_key="bowl_weight",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:bowl-mix",
        value_fn=lambda device: device.device_prop.get("bowlWeight"),
    ),
    PawsyncSensorEntityDescription(
        key="bucket_surplus",
        translation_key="bucket_surplus",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:database",
        value_fn=lambda device: device.device_prop.get("petFood", {}).get(
            "bucketSurplus"
        ),
    ),
    PawsyncSensorEntityDescription(
        key="last_feeding_amount",
        translation_key="last_feeding_amount",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shaker",
        value_fn=lambda device: device.device_prop.get("petFood", {}).get(
            "lastFeedingAmount"
        ),
    ),
    PawsyncSensorEntityDescription(
        key="content_remain_time",
        translation_key="content_remain_time",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:calendar-clock",
        value_fn=lambda device: device.device_prop.get("petFood", {}).get(
            "contentRemainTime"
        ),
    ),
    PawsyncSensorEntityDescription(
        key="battery_percent",
        translation_key="battery_percent",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.device_prop.get("batteryPercent"),
    ),
    PawsyncSensorEntityDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.device_prop.get("wifiRssi"),
    ),
    PawsyncSensorEntityDescription(
        key="alert_count",
        translation_key="alert_count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alert-circle",
        value_fn=lambda device: device.device_prop.get("alertCount"),
    ),
    PawsyncSensorEntityDescription(
        key="main_fw_version",
        translation_key="main_fw_version",
        icon="mdi:chip",
        value_fn=lambda device: next(
            (
                fw["version"]
                for fw in device.device_prop.get("firmwareInfos", [])
                if fw.get("isMainFw")
            ),
            None,
        ),
    ),
    PawsyncSensorEntityDescription(
        key="mcu_fw_version",
        translation_key="mcu_fw_version",
        icon="mdi:cpu-64-bit",
        value_fn=lambda device: next(
            (
                fw["version"]
                for fw in device.device_prop.get("firmwareInfos", [])
                if fw.get("pluginName") == "mcuFw"
            ),
            None,
        ),
    ),
)


@dataclass(frozen=True, kw_only=True)
class PawsyncLogSensorEntityDescription(SensorEntityDescription):
    """Class describing Pawsync log sensor entities."""

    log_fn: Callable[[list], Any] | None = None


LOG_SENSOR_TYPES: tuple[PawsyncLogSensorEntityDescription, ...] = (
    PawsyncLogSensorEntityDescription(
        key="last_dispensed_time",
        translation_key="last_dispensed_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-check",
        log_fn=lambda logs: next(
            (
                datetime.fromtimestamp(e["timestamp"], tz=UTC)
                for e in logs
                if e["logType"] in ("planFeeding", "manualFeeding")
            ),
            None,
        ),
    ),
    PawsyncLogSensorEntityDescription(
        key="last_dispensed_amount",
        translation_key="last_dispensed_amount",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shaker-outline",
        log_fn=lambda logs: next(
            (
                e["value"]
                for e in logs
                if e["logType"] in ("planFeeding", "manualFeeding")
                and e.get("value") is not None
            ),
            None,
        ),
    ),
    PawsyncLogSensorEntityDescription(
        key="last_eaten_time",
        translation_key="last_eaten_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:cat",
        log_fn=lambda logs: next(
            (
                datetime.fromtimestamp(e["timestamp"], tz=UTC)
                for e in logs
                if e["logType"] == "takeFood"
            ),
            None,
        ),
    ),
    PawsyncLogSensorEntityDescription(
        key="last_eaten_amount",
        translation_key="last_eaten_amount",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:food-variant",
        log_fn=lambda logs: next(
            (
                e["value"]
                for e in logs
                if e["logType"] == "takeFood" and e.get("value") is not None
            ),
            None,
        ),
    ),
    PawsyncLogSensorEntityDescription(
        key="last_eating_duration",
        translation_key="last_eating_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer",
        log_fn=lambda logs: next(
            (
                e["durationInS"]
                for e in logs
                if e["logType"] == "takeFood" and e.get("durationInS", -1) > 0
            ),
            None,
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PawsyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pawsync sensor entities from a config entry."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = []
    for device_id in coordinator.data.devices:
        for description in SENSOR_TYPES:
            entities.append(PawsyncDeviceSensor(coordinator, device_id, description))
        for description in LOG_SENSOR_TYPES:
            entities.append(PawsyncLogSensor(coordinator, device_id, description))

    async_add_entities(entities)

    async_register_entity_services(entity_platform.async_get_current_platform())


class PawsyncDeviceSensor(PawsyncEntity, SensorEntity):
    """Representation of a Pawsync device property as a sensor."""

    entity_description: PawsyncSensorEntityDescription

    def __init__(
        self,
        coordinator: PawsyncDataUpdateCoordinator,
        device_id: str,
        description: PawsyncSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.device)
        return None

    async def async_request_feed(self, amount: int) -> None:
        """Request a manual feed for this device."""
        client = self.coordinator.client
        try:
            await client.async_request_feed(self.device, amount)
        except PawsyncAuthError:
            await client.async_login()
            await client.async_request_feed(self.device, amount)
        except PawsyncApiError as err:
            raise HomeAssistantError(f"Feed request failed: {err}") from err

        self.coordinator.request_fast_poll()
        await self.coordinator.async_request_refresh()


class PawsyncLogSensor(PawsyncEntity, SensorEntity):
    """Representation of Pawsync pet log activity as a sensor."""

    entity_description: PawsyncLogSensorEntityDescription

    def __init__(
        self,
        coordinator: PawsyncDataUpdateCoordinator,
        device_id: str,
        description: PawsyncLogSensorEntityDescription,
    ) -> None:
        """Initialize the log sensor."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def _logs(self) -> list:
        return self.coordinator.data.pet_logs.get(self._device_id, [])

    @property
    def native_value(self) -> Any:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the state of the sensor."""
        if not self.entity_description.log_fn:
            return None
        return self.entity_description.log_fn(self._logs)
