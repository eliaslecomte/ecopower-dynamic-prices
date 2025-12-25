"""Number entities for Ecopower Dynamic Prices cost parameters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUMBER_ENTITIES

if TYPE_CHECKING:
    from . import EcopowerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from a config entry."""
    coordinator: EcopowerDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[EcopowerCostNumber] = []

    for param_key, config in NUMBER_ENTITIES.items():
        # Get initial value from options or use default
        initial_value = config_entry.options.get(param_key, config["default"])

        entities.append(
            EcopowerCostNumber(
                coordinator=coordinator,
                config_entry=config_entry,
                param_key=param_key,
                name=config["name"],
                min_value=config["min"],
                max_value=config["max"],
                step=config["step"],
                unit=config["unit"],
                icon=config["icon"],
                initial_value=initial_value,
            )
        )

    async_add_entities(entities)

    # Store references to number entities in coordinator for easy access
    for entity in entities:
        coordinator.register_number_entity(entity.param_key, entity)


class EcopowerCostNumber(RestoreNumber):
    """Editable number entity for cost parameters."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcopowerDataUpdateCoordinator,
        config_entry: ConfigEntry,
        param_key: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None,
        icon: str,
        initial_value: float,
    ) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._param_key = param_key

        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_{param_key}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_native_value = initial_value

    @property
    def param_key(self) -> str:
        """Return the parameter key."""
        return self._param_key

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="Ecopower Dynamic Prices",
            manufacturer="Ecopower",
            model="Dynamic Price Calculator",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last known state when added to hass."""
        await super().async_added_to_hass()

        # Try to restore the last known value
        last_number_data = await self.async_get_last_number_data()

        if last_number_data is not None and last_number_data.native_value is not None:
            self._attr_native_value = last_number_data.native_value
            _LOGGER.debug(
                "Restored %s to %s", self._param_key, self._attr_native_value
            )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()

        _LOGGER.debug("Set %s to %s", self._param_key, value)

        # Trigger coordinator refresh to recalculate prices
        await self.coordinator.async_request_refresh()
