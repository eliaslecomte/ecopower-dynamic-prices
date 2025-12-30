"""Constants for the Ecopower Dynamic Prices integration."""

from typing import Final

DOMAIN: Final = "ecopower_dynamic_prices"

# Configuration keys
CONF_SOURCE_ENTITY: Final = "source_entity_id"
CONF_SOURCE_TYPE: Final = "source_type"

# Source types
SOURCE_TYPE_EPEX_SPOT: Final = "epex_spot"
SOURCE_TYPE_ENERGI_DATA_SERVICE: Final = "energi_data_service"

# Ecopower-specific cost parameters
CONF_CONSUMPTION_MULTIPLIER: Final = "consumption_multiplier"
CONF_SUPPLIER_COST: Final = "supplier_cost"
CONF_INJECTION_MULTIPLIER: Final = "injection_multiplier"
CONF_INJECTION_DEDUCTION: Final = "injection_deduction"

# Belgian energy cost parameters
CONF_GREEN_CERTIFICATES: Final = "green_certificates"
CONF_CHP_CERTIFICATES: Final = "chp_certificates"
CONF_DISTRIBUTION_COST: Final = "distribution_cost"
CONF_ENERGY_CONTRIBUTION: Final = "energy_contribution"
CONF_EXCISE_TAX: Final = "excise_tax"
CONF_VAT_RATE: Final = "vat_rate"

# Default values - Ecopower-specific
DEFAULT_CONSUMPTION_MULTIPLIER: Final = 1.02  # 2% Ecopower margin
DEFAULT_SUPPLIER_COST: Final = 0.004  # €/kWh Ecopower admin cost
DEFAULT_INJECTION_MULTIPLIER: Final = 0.98  # 2% Ecopower margin
DEFAULT_INJECTION_DEDUCTION: Final = 0.015  # €/kWh Ecopower fee

# Default values - Belgian energy costs
DEFAULT_GREEN_CERTIFICATES: Final = 0.011  # €/kWh GSC (Groene Stroom Certificaten)
DEFAULT_CHP_CERTIFICATES: Final = 0.0039  # €/kWh WKK (Warmte-Kracht Koppeling)
DEFAULT_DISTRIBUTION_COST: Final = 0.0589  # €/kWh Afname Tarief
DEFAULT_ENERGY_CONTRIBUTION: Final = 0.0019  # €/kWh Bijdrage op Energie
DEFAULT_EXCISE_TAX: Final = 0.0475  # €/kWh Bijzondere Accijns
DEFAULT_VAT_RATE: Final = 6.0  # 6% VAT as percentage

# Number entity configuration
NUMBER_ENTITIES: Final = {
    # Ecopower-specific
    CONF_CONSUMPTION_MULTIPLIER: {
        "name": "Consumption Multiplier",
        "min": 0.5,
        "max": 2.0,
        "step": 0.01,
        "unit": None,
        "default": DEFAULT_CONSUMPTION_MULTIPLIER,
        "icon": "mdi:percent",
    },
    CONF_SUPPLIER_COST: {
        "name": "Ecopower Tariff",
        "min": 0.0,
        "max": 0.1,
        "step": 0.0001,
        "unit": "€/kWh",
        "default": DEFAULT_SUPPLIER_COST,
        "icon": "mdi:currency-eur",
    },
    CONF_INJECTION_MULTIPLIER: {
        "name": "Injection Multiplier",
        "min": 0.5,
        "max": 1.5,
        "step": 0.01,
        "unit": None,
        "default": DEFAULT_INJECTION_MULTIPLIER,
        "icon": "mdi:percent",
    },
    CONF_INJECTION_DEDUCTION: {
        "name": "Injection Deduction",
        "min": 0.0,
        "max": 0.1,
        "step": 0.0001,
        "unit": "€/kWh",
        "default": DEFAULT_INJECTION_DEDUCTION,
        "icon": "mdi:currency-eur",
    },
    # Belgian energy costs
    CONF_GREEN_CERTIFICATES: {
        "name": "GSC (Groene Stroom)",
        "min": 0.0,
        "max": 0.1,
        "step": 0.0001,
        "unit": "€/kWh",
        "default": DEFAULT_GREEN_CERTIFICATES,
        "icon": "mdi:leaf",
    },
    CONF_CHP_CERTIFICATES: {
        "name": "WKK",
        "min": 0.0,
        "max": 0.1,
        "step": 0.0001,
        "unit": "€/kWh",
        "default": DEFAULT_CHP_CERTIFICATES,
        "icon": "mdi:cog",
    },
    CONF_DISTRIBUTION_COST: {
        "name": "Afname Tarief",
        "min": 0.0,
        "max": 0.2,
        "step": 0.0001,
        "unit": "€/kWh",
        "default": DEFAULT_DISTRIBUTION_COST,
        "icon": "mdi:transmission-tower",
    },
    CONF_ENERGY_CONTRIBUTION: {
        "name": "Bijdrage Energie",
        "min": 0.0,
        "max": 0.1,
        "step": 0.0001,
        "unit": "€/kWh",
        "default": DEFAULT_ENERGY_CONTRIBUTION,
        "icon": "mdi:lightning-bolt",
    },
    CONF_EXCISE_TAX: {
        "name": "Bijzondere Accijns",
        "min": 0.0,
        "max": 0.2,
        "step": 0.0001,
        "unit": "€/kWh",
        "default": DEFAULT_EXCISE_TAX,
        "icon": "mdi:bank",
    },
    CONF_VAT_RATE: {
        "name": "BTW / VAT Rate",
        "min": 0,
        "max": 30,
        "step": 1,
        "unit": "%",
        "default": DEFAULT_VAT_RATE,
        "icon": "mdi:percent",
    },
}

# Attribute keys for sensors
ATTR_DATA: Final = "data"
ATTR_RAW_TODAY: Final = "raw_today"
ATTR_RAW_TOMORROW: Final = "raw_tomorrow"
ATTR_TODAY: Final = "today"
ATTR_TOMORROW: Final = "tomorrow"
ATTR_TODAY_MIN: Final = "today_min"
ATTR_TODAY_MAX: Final = "today_max"
ATTR_TODAY_MEAN: Final = "today_mean"
ATTR_TOMORROW_MIN: Final = "tomorrow_min"
ATTR_TOMORROW_MAX: Final = "tomorrow_max"
ATTR_TOMORROW_MEAN: Final = "tomorrow_mean"
ATTR_TOMORROW_VALID: Final = "tomorrow_valid"
ATTR_SOURCE_ENTITY: Final = "source_entity"
ATTR_START_TIME: Final = "start_time"
ATTR_END_TIME: Final = "end_time"
ATTR_PRICE_PER_KWH: Final = "price_per_kwh"
ATTR_HOUR: Final = "hour"
ATTR_PRICE: Final = "price"
