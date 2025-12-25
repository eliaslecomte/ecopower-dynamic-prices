"""The Ecopower Dynamic Prices integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .calculations import (
    CostParameters,
    calculate_all_prices,
)
from .const import (
    CONF_SOURCE_ENTITY,
    CONF_SOURCE_TYPE,
    DOMAIN,
    NUMBER_ENTITIES,
)
from .parsers import get_parser_by_type

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

# Update interval for periodic refresh (as backup to state change events)
UPDATE_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecopower Dynamic Prices from a config entry."""
    source_entity_id = entry.data[CONF_SOURCE_ENTITY]
    source_type = entry.data[CONF_SOURCE_TYPE]

    # Validate source sensor exists
    source_state = hass.states.get(source_entity_id)
    if source_state is None:
        raise ConfigEntryNotReady(f"Source sensor {source_entity_id} not available")

    # Get the parser for this source type
    parser = get_parser_by_type(source_type)
    if parser is None:
        raise ConfigEntryNotReady(f"No parser available for source type {source_type}")

    # Create the coordinator
    coordinator = EcopowerDataUpdateCoordinator(
        hass,
        entry,
        source_entity_id,
        parser,
    )

    # Do initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for source sensor state changes
    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            [source_entity_id],
            coordinator.async_source_state_changed,
        )
    )

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: EcopowerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_request_refresh()


class EcopowerDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Ecopower Dynamic Prices data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        source_entity_id: str,
        parser,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self.source_entity_id = source_entity_id
        self.parser = parser
        self._number_entities: dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    def register_number_entity(self, param_key: str, entity) -> None:
        """Register a number entity for parameter access."""
        self._number_entities[param_key] = entity

    def _get_cost_parameters(self) -> CostParameters:
        """Get current cost parameters from number entities or config."""
        params = {}

        for param_key in NUMBER_ENTITIES:
            # First try to get from number entity
            if param_key in self._number_entities:
                entity = self._number_entities[param_key]
                if entity.native_value is not None:
                    params[param_key] = entity.native_value
                    continue

            # Fall back to config options
            if param_key in self.config_entry.options:
                params[param_key] = self.config_entry.options[param_key]

        return CostParameters.from_dict(params)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and calculate prices."""
        # Get source sensor state
        source_state = self.hass.states.get(self.source_entity_id)

        if source_state is None:
            raise UpdateFailed(f"Source sensor {self.source_entity_id} not available")

        attributes = source_state.attributes
        if not attributes:
            raise UpdateFailed(
                f"Source sensor {self.source_entity_id} has no attributes"
            )

        # Parse source data
        try:
            parsed_data = self.parser.parse_prices(attributes)
        except Exception as err:
            raise UpdateFailed(f"Failed to parse price data: {err}") from err

        if not parsed_data.today:
            raise UpdateFailed("No price data available for today")

        # Get cost parameters
        params = self._get_cost_parameters()

        # Calculate all prices
        consumption_data, injection_data = calculate_all_prices(parsed_data, params)

        return {
            "consumption": consumption_data,
            "injection": injection_data,
        }

    @callback
    def async_source_state_changed(self, event) -> None:
        """Handle source sensor state change."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        _LOGGER.debug("Source sensor %s changed, refreshing", self.source_entity_id)

        # Schedule a refresh
        self.hass.async_create_task(self.async_request_refresh())
