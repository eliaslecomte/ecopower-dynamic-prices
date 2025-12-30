"""Config flow for Ecopower Dynamic Prices integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_CHP_CERTIFICATES,
    CONF_CONSUMPTION_MULTIPLIER,
    CONF_DISTRIBUTION_COST,
    CONF_ENERGY_CONTRIBUTION,
    CONF_EXCISE_TAX,
    CONF_GREEN_CERTIFICATES,
    CONF_INJECTION_DEDUCTION,
    CONF_INJECTION_MULTIPLIER,
    CONF_SOURCE_ENTITY,
    CONF_SOURCE_TYPE,
    CONF_SUPPLIER_COST,
    CONF_VAT_RATE,
    DEFAULT_CHP_CERTIFICATES,
    DEFAULT_CONSUMPTION_MULTIPLIER,
    DEFAULT_DISTRIBUTION_COST,
    DEFAULT_ENERGY_CONTRIBUTION,
    DEFAULT_EXCISE_TAX,
    DEFAULT_GREEN_CERTIFICATES,
    DEFAULT_INJECTION_DEDUCTION,
    DEFAULT_INJECTION_MULTIPLIER,
    DEFAULT_SUPPLIER_COST,
    DEFAULT_VAT_RATE,
    DOMAIN,
)
from .parsers import analyze_sensor_shape, get_parser_for_attributes

_LOGGER = logging.getLogger(__name__)


def _validate_source_sensor(
    hass: HomeAssistant, entity_id: str
) -> tuple[bool, str | None]:
    """Validate that the source sensor can be parsed.

    Returns:
        Tuple of (is_valid, source_type or error_key)
    """
    try:
        state = hass.states.get(entity_id)

        if state is None:
            _LOGGER.debug("Sensor %s not found", entity_id)
            return False, "sensor_not_found"

        attributes = state.attributes
        if not attributes:
            _LOGGER.debug("Sensor %s has no attributes", entity_id)
            return False, "no_attributes"

        _LOGGER.debug(
            "Validating sensor %s with %d attributes: %s",
            entity_id,
            len(attributes),
            list(attributes.keys()),
        )

        # Use shape analyzer to detect format
        shape_info = analyze_sensor_shape(attributes)
        _LOGGER.debug(
            "Shape analysis for %s: type=%s, reason=%s, details=%s",
            entity_id,
            shape_info["detected_type"],
            shape_info["reason"],
            shape_info.get("details", {}),
        )

        if shape_info["detected_type"] is None:
            _LOGGER.warning(
                "Cannot parse sensor %s: %s. Details: %s",
                entity_id,
                shape_info["reason"],
                shape_info.get("details", {}),
            )
            return False, "cannot_parse"

        _LOGGER.debug(
            "Successfully detected sensor %s as type: %s",
            entity_id,
            shape_info["detected_type"],
        )
        return True, shape_info["detected_type"]

    except Exception as err:
        _LOGGER.exception("Error validating sensor %s: %s", entity_id, err)
        return False, "unknown_error"


class EcopowerDynamicPricesConfigFlow(
    config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle a config flow for Ecopower Dynamic Prices."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._source_entity_id: str | None = None
        self._source_type: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - source sensor selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_SOURCE_ENTITY]

            # Validate the sensor
            is_valid, result = _validate_source_sensor(self.hass, entity_id)

            if is_valid:
                try:
                    self._source_entity_id = entity_id
                    self._source_type = result

                    # Check for duplicate entry
                    await self.async_set_unique_id(entity_id)
                    self._abort_if_unique_id_configured()

                    # Proceed to cost parameters step
                    return await self.async_step_costs()
                except Exception as err:
                    _LOGGER.exception("Error after validation for %s: %s", entity_id, err)
                    errors["base"] = "unknown_error"
            else:
                errors["base"] = result

        # Show the form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_costs(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the cost parameters step."""
        if user_input is not None:
            # Create the config entry
            return self.async_create_entry(
                title=f"Ecopower ({self._source_entity_id})",
                data={
                    CONF_SOURCE_ENTITY: self._source_entity_id,
                    CONF_SOURCE_TYPE: self._source_type,
                },
                options=user_input,
            )

        # Show the form with default values
        data_schema = vol.Schema(
            {
                # Ecopower-specific
                vol.Required(
                    CONF_CONSUMPTION_MULTIPLIER,
                    default=DEFAULT_CONSUMPTION_MULTIPLIER,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=2.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_SUPPLIER_COST,
                    default=DEFAULT_SUPPLIER_COST,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_INJECTION_MULTIPLIER,
                    default=DEFAULT_INJECTION_MULTIPLIER,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=1.5,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_INJECTION_DEDUCTION,
                    default=DEFAULT_INJECTION_DEDUCTION,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                # Belgian energy costs
                vol.Required(
                    CONF_GREEN_CERTIFICATES,
                    default=DEFAULT_GREEN_CERTIFICATES,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_CHP_CERTIFICATES,
                    default=DEFAULT_CHP_CERTIFICATES,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_DISTRIBUTION_COST,
                    default=DEFAULT_DISTRIBUTION_COST,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.2,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_ENERGY_CONTRIBUTION,
                    default=DEFAULT_ENERGY_CONTRIBUTION,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_EXCISE_TAX,
                    default=DEFAULT_EXCISE_TAX,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.2,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_VAT_RATE,
                    default=DEFAULT_VAT_RATE,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=30,
                        step=1,
                        unit_of_measurement="%",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="costs",
            data_schema=data_schema,
            description_placeholders={
                "source_entity": self._source_entity_id,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return EcopowerDynamicPricesOptionsFlow(config_entry)


class EcopowerDynamicPricesOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Ecopower Dynamic Prices."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        data_schema = vol.Schema(
            {
                # Ecopower-specific
                vol.Required(
                    CONF_CONSUMPTION_MULTIPLIER,
                    default=options.get(
                        CONF_CONSUMPTION_MULTIPLIER, DEFAULT_CONSUMPTION_MULTIPLIER
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=2.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_SUPPLIER_COST,
                    default=options.get(CONF_SUPPLIER_COST, DEFAULT_SUPPLIER_COST),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_INJECTION_MULTIPLIER,
                    default=options.get(
                        CONF_INJECTION_MULTIPLIER, DEFAULT_INJECTION_MULTIPLIER
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=1.5,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_INJECTION_DEDUCTION,
                    default=options.get(
                        CONF_INJECTION_DEDUCTION, DEFAULT_INJECTION_DEDUCTION
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                # Belgian energy costs
                vol.Required(
                    CONF_GREEN_CERTIFICATES,
                    default=options.get(
                        CONF_GREEN_CERTIFICATES, DEFAULT_GREEN_CERTIFICATES
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_CHP_CERTIFICATES,
                    default=options.get(
                        CONF_CHP_CERTIFICATES, DEFAULT_CHP_CERTIFICATES
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_DISTRIBUTION_COST,
                    default=options.get(
                        CONF_DISTRIBUTION_COST, DEFAULT_DISTRIBUTION_COST
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.2,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_ENERGY_CONTRIBUTION,
                    default=options.get(
                        CONF_ENERGY_CONTRIBUTION, DEFAULT_ENERGY_CONTRIBUTION
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.1,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_EXCISE_TAX,
                    default=options.get(CONF_EXCISE_TAX, DEFAULT_EXCISE_TAX),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=0.2,
                        step="any",
                        unit_of_measurement="€/kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_VAT_RATE,
                    default=options.get(CONF_VAT_RATE, DEFAULT_VAT_RATE),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=30,
                        step=1,
                        unit_of_measurement="%",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
