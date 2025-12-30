"""Price calculation functions for Ecopower Dynamic Prices."""

from dataclasses import dataclass
from statistics import mean

from .const import (
    CONF_CHP_CERTIFICATES,
    CONF_CONSUMPTION_MULTIPLIER,
    CONF_DISTRIBUTION_COST,
    CONF_ENERGY_CONTRIBUTION,
    CONF_EXCISE_TAX,
    CONF_GREEN_CERTIFICATES,
    CONF_INJECTION_DEDUCTION,
    CONF_INJECTION_MULTIPLIER,
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
)
from .parsers import ParsedPriceData, PriceEntry


@dataclass
class CostParameters:
    """Container for all cost parameters."""

    # Ecopower-specific
    consumption_multiplier: float = DEFAULT_CONSUMPTION_MULTIPLIER
    supplier_cost: float = DEFAULT_SUPPLIER_COST
    injection_multiplier: float = DEFAULT_INJECTION_MULTIPLIER
    injection_deduction: float = DEFAULT_INJECTION_DEDUCTION

    # Belgian energy costs
    green_certificates: float = DEFAULT_GREEN_CERTIFICATES
    chp_certificates: float = DEFAULT_CHP_CERTIFICATES
    distribution_cost: float = DEFAULT_DISTRIBUTION_COST
    energy_contribution: float = DEFAULT_ENERGY_CONTRIBUTION
    excise_tax: float = DEFAULT_EXCISE_TAX
    vat_rate: float = DEFAULT_VAT_RATE

    @classmethod
    def from_dict(cls, data: dict) -> "CostParameters":
        """Create CostParameters from a dictionary."""
        return cls(
            consumption_multiplier=data.get(
                CONF_CONSUMPTION_MULTIPLIER, DEFAULT_CONSUMPTION_MULTIPLIER
            ),
            supplier_cost=data.get(CONF_SUPPLIER_COST, DEFAULT_SUPPLIER_COST),
            injection_multiplier=data.get(
                CONF_INJECTION_MULTIPLIER, DEFAULT_INJECTION_MULTIPLIER
            ),
            injection_deduction=data.get(
                CONF_INJECTION_DEDUCTION, DEFAULT_INJECTION_DEDUCTION
            ),
            green_certificates=data.get(
                CONF_GREEN_CERTIFICATES, DEFAULT_GREEN_CERTIFICATES
            ),
            chp_certificates=data.get(CONF_CHP_CERTIFICATES, DEFAULT_CHP_CERTIFICATES),
            distribution_cost=data.get(
                CONF_DISTRIBUTION_COST, DEFAULT_DISTRIBUTION_COST
            ),
            energy_contribution=data.get(
                CONF_ENERGY_CONTRIBUTION, DEFAULT_ENERGY_CONTRIBUTION
            ),
            excise_tax=data.get(CONF_EXCISE_TAX, DEFAULT_EXCISE_TAX),
            vat_rate=data.get(CONF_VAT_RATE, DEFAULT_VAT_RATE),
        )


def calculate_consumption_price(
    market_price: float,
    params: CostParameters,
) -> float:
    """Calculate consumption price with all costs applied.

    Formula: ((market_price * consumption_multiplier) + all_costs) * (1 + vat_rate / 100)

    Args:
        market_price: The raw market price in €/kWh
        params: Cost parameters to apply

    Returns:
        The calculated consumption price in €/kWh, rounded to 4 decimals
    """
    base = market_price * params.consumption_multiplier

    total_costs = (
        params.supplier_cost
        + params.green_certificates
        + params.chp_certificates
        + params.distribution_cost
        + params.energy_contribution
        + params.excise_tax
    )

    # Convert VAT percentage to multiplier (e.g., 6% -> 1.06)
    vat_multiplier = 1 + (params.vat_rate / 100)

    return round((base + total_costs) * vat_multiplier, 4)


def calculate_injection_price(
    market_price: float,
    params: CostParameters,
) -> float:
    """Calculate injection price with deductions applied.

    Formula: (market_price * injection_multiplier) - injection_deduction

    Args:
        market_price: The raw market price in €/kWh
        params: Cost parameters to apply

    Returns:
        The calculated injection price in €/kWh, rounded to 4 decimals
    """
    return round(
        (market_price * params.injection_multiplier) - params.injection_deduction, 4
    )


@dataclass
class CalculatedPriceEntry:
    """A calculated price entry with time range and prices."""

    start_time: str  # ISO format string
    end_time: str  # ISO format string
    price_per_kwh: float


@dataclass
class CalculatedPriceData:
    """Calculated price data for consumption or injection."""

    current_price: float | None = None

    # Detailed format (like EPEX)
    data: list[CalculatedPriceEntry] | None = None

    # Simplified format (like Energi Data Service)
    raw_today: list[dict] | None = None
    raw_tomorrow: list[dict] | None = None
    today: list[float] | None = None
    tomorrow: list[float] | None = None

    # Statistics
    today_min: float | None = None
    today_max: float | None = None
    today_mean: float | None = None
    tomorrow_min: float | None = None
    tomorrow_max: float | None = None
    tomorrow_mean: float | None = None
    tomorrow_valid: bool = False


def calculate_all_prices(
    parsed_data: ParsedPriceData,
    params: CostParameters,
) -> tuple[CalculatedPriceData, CalculatedPriceData]:
    """Calculate consumption and injection prices for all time slots.

    Args:
        parsed_data: Parsed price data from source sensor
        params: Cost parameters to apply

    Returns:
        Tuple of (consumption_data, injection_data)
    """
    consumption = _calculate_price_data(
        parsed_data,
        params,
        calculate_consumption_price,
    )

    injection = _calculate_price_data(
        parsed_data,
        params,
        calculate_injection_price,
    )

    return consumption, injection


def _calculate_price_data(
    parsed_data: ParsedPriceData,
    params: CostParameters,
    price_func,
) -> CalculatedPriceData:
    """Calculate price data using the given price function."""
    # Calculate current price
    current_price = None
    if parsed_data.current_price is not None:
        current_price = price_func(parsed_data.current_price, params)

    # Calculate today's prices
    today_data: list[CalculatedPriceEntry] = []
    today_raw: list[dict] = []
    today_prices: list[float] = []

    for entry in parsed_data.today:
        calculated_price = price_func(entry.price, params)
        today_prices.append(calculated_price)

        today_data.append(
            CalculatedPriceEntry(
                start_time=entry.start_time.isoformat(),
                end_time=entry.end_time.isoformat(),
                price_per_kwh=calculated_price,
            )
        )

        today_raw.append(
            {
                "hour": entry.start_time.isoformat(),
                "price": calculated_price,
            }
        )

    # Calculate tomorrow's prices
    tomorrow_data: list[CalculatedPriceEntry] = []
    tomorrow_raw: list[dict] = []
    tomorrow_prices: list[float] = []

    for entry in parsed_data.tomorrow:
        calculated_price = price_func(entry.price, params)
        tomorrow_prices.append(calculated_price)

        tomorrow_data.append(
            CalculatedPriceEntry(
                start_time=entry.start_time.isoformat(),
                end_time=entry.end_time.isoformat(),
                price_per_kwh=calculated_price,
            )
        )

        tomorrow_raw.append(
            {
                "hour": entry.start_time.isoformat(),
                "price": calculated_price,
            }
        )

    # Combine data for detailed format
    all_data = today_data + tomorrow_data

    # Calculate statistics
    today_min = min(today_prices) if today_prices else None
    today_max = max(today_prices) if today_prices else None
    today_mean = round(mean(today_prices), 4) if today_prices else None

    tomorrow_min = min(tomorrow_prices) if tomorrow_prices else None
    tomorrow_max = max(tomorrow_prices) if tomorrow_prices else None
    tomorrow_mean = round(mean(tomorrow_prices), 4) if tomorrow_prices else None

    return CalculatedPriceData(
        current_price=current_price,
        data=[
            {
                "start_time": e.start_time,
                "end_time": e.end_time,
                "price_per_kwh": e.price_per_kwh,
            }
            for e in all_data
        ]
        if all_data
        else None,
        raw_today=today_raw if today_raw else None,
        raw_tomorrow=tomorrow_raw if tomorrow_raw else None,
        today=today_prices if today_prices else None,
        tomorrow=tomorrow_prices if tomorrow_prices else None,
        today_min=today_min,
        today_max=today_max,
        today_mean=today_mean,
        tomorrow_min=tomorrow_min,
        tomorrow_max=tomorrow_max,
        tomorrow_mean=tomorrow_mean,
        tomorrow_valid=parsed_data.tomorrow_valid,
    )
