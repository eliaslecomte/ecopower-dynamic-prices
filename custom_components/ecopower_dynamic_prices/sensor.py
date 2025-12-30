"""Sensor entities for Ecopower Dynamic Prices."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DATA,
    ATTR_RAW_TODAY,
    ATTR_RAW_TOMORROW,
    ATTR_SOURCE_ENTITY,
    ATTR_TODAY,
    ATTR_TODAY_MAX,
    ATTR_TODAY_MEAN,
    ATTR_TODAY_MIN,
    ATTR_TOMORROW,
    ATTR_TOMORROW_MAX,
    ATTR_TOMORROW_MEAN,
    ATTR_TOMORROW_MIN,
    ATTR_TOMORROW_VALID,
    CONF_SOURCE_ENTITY,
    DOMAIN,
)

if TYPE_CHECKING:
    from . import EcopowerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: EcopowerDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        EcopowerConsumptionPriceSensor(coordinator, config_entry),
        EcopowerInjectionPriceSensor(coordinator, config_entry),
    ]

    async_add_entities(entities)


class EcopowerBasePriceSensor(CoordinatorEntity, SensorEntity):
    """Base class for Ecopower price sensors."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "€/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 4

    # Attributes that should not be recorded in history (large arrays)
    _unrecorded_attributes = frozenset(
        {
            ATTR_DATA,
            ATTR_RAW_TODAY,
            ATTR_RAW_TOMORROW,
            ATTR_TODAY,
            ATTR_TOMORROW,
        }
    )

    def __init__(
        self,
        coordinator: EcopowerDataUpdateCoordinator,
        config_entry: ConfigEntry,
        name: str,
        unique_id_suffix: str,
        data_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._data_key = data_key

        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_{unique_id_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._config_entry.title,
            manufacturer="Ecopower",
            model="Dynamic Price Calculator",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        if self.coordinator.data is None:
            return None

        price_data = self.coordinator.data.get(self._data_key)
        if price_data is None:
            return None

        return price_data.current_price

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if self.coordinator.data is None:
            return {}

        price_data = self.coordinator.data.get(self._data_key)
        if price_data is None:
            return {}

        return {
            # Detailed format (like EPEX Spot)
            ATTR_DATA: price_data.data,
            # Simplified format (like Energi Data Service)
            ATTR_RAW_TODAY: price_data.raw_today,
            ATTR_RAW_TOMORROW: price_data.raw_tomorrow,
            ATTR_TODAY: price_data.today,
            ATTR_TOMORROW: price_data.tomorrow,
            # Statistics
            ATTR_TODAY_MIN: price_data.today_min,
            ATTR_TODAY_MAX: price_data.today_max,
            ATTR_TODAY_MEAN: price_data.today_mean,
            ATTR_TOMORROW_MIN: price_data.tomorrow_min,
            ATTR_TOMORROW_MAX: price_data.tomorrow_max,
            ATTR_TOMORROW_MEAN: price_data.tomorrow_mean,
            ATTR_TOMORROW_VALID: price_data.tomorrow_valid,
            # Source info
            ATTR_SOURCE_ENTITY: self._config_entry.data.get(CONF_SOURCE_ENTITY),
        }


class EcopowerConsumptionPriceSensor(EcopowerBasePriceSensor):
    """Sensor for consumption price with all costs applied."""

    _attr_icon = "mdi:home-lightning-bolt"

    def __init__(
        self,
        coordinator: EcopowerDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the consumption price sensor."""
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Consumption Price",
            unique_id_suffix="consumption_price",
            data_key="consumption",
        )


class EcopowerInjectionPriceSensor(EcopowerBasePriceSensor):
    """Sensor for injection price with deductions applied."""

    _attr_icon = "mdi:solar-power"

    def __init__(
        self,
        coordinator: EcopowerDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the injection price sensor."""
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Injection Price",
            unique_id_suffix="injection_price",
            data_key="injection",
        )
