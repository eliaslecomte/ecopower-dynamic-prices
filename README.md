# Ecopower Dynamic Prices

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant integration that calculates real electricity prices for Ecopower customers in Belgium, including all taxes, fees, and supplier margins.

## Features

- **Parses existing price sensors** from EPEX Spot or Energi Data Service integrations
- **Calculates consumption prices** with all Belgian energy costs and Ecopower margins
- **Calculates injection prices** with Ecopower deductions
- **Editable cost parameters** via number entities - change values at runtime
- **Full price arrays** in sensor attributes for easy charting with ApexCharts

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/eliaslecomte/ecopower-dynamic-prices` as an Integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ecopower_dynamic_prices` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Ecopower Dynamic Prices"
4. Select your source sensor (from EPEX Spot or Energi Data Service)
5. Configure cost parameters (defaults are provided for Ecopower Belgium)

## Supported Source Integrations

- [EPEX Spot](https://github.com/mampfes/ha_epex_spot)
- [Energi Data Service](https://github.com/MTrab/energidataservice)

## Entities Created

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.ecopower_consumption_price` | Current consumption price with all costs |
| `sensor.ecopower_injection_price` | Current injection price with deductions |

### Number Entities (Editable)

**Ecopower-specific:**

| Entity | Default | Description |
|--------|---------|-------------|
| `number.ecopower_consumption_multiplier` | 1.02 | Ecopower margin on market price |
| `number.ecopower_supplier_cost` | 0.004 €/kWh | Ecopower administrative cost |
| `number.ecopower_injection_multiplier` | 0.98 | Ecopower margin on injection |
| `number.ecopower_injection_deduction` | 0.015 €/kWh | Ecopower injection fee |

**Belgian Energy Costs:**

| Entity | Default | Description |
|--------|---------|-------------|
| `number.ecopower_green_certificates` | 0.011 €/kWh | GSC (Groene Stroom) |
| `number.ecopower_chp_certificates` | 0.0039 €/kWh | WKK certificates |
| `number.ecopower_distribution_cost` | 0.0589 €/kWh | Afname Tarief |
| `number.ecopower_energy_contribution` | 0.0019 €/kWh | Bijdrage Energie |
| `number.ecopower_excise_tax` | 0.0475 €/kWh | Bijzondere Accijns |
| `number.ecopower_vat_rate` | 1.06 | BTW (6% VAT) |

## Price Formulas

### Consumption Price
```
((market_price × consumption_multiplier) + all_costs) × vat_rate
```

Where `all_costs` = supplier_cost + green_certificates + chp_certificates + distribution_cost + energy_contribution + excise_tax

### Injection Price

```
(market_price × injection_multiplier) - injection_deduction
```

## Sensor Attributes

Both sensors include rich attributes for charting:

```yaml
# Detailed format (like EPEX Spot)
data:
  - start_time: '2025-12-25T00:00:00+01:00'
    end_time: '2025-12-25T00:15:00+01:00'
    price_per_kwh: 0.1892

# Simplified format (like Energi Data Service)
raw_today:
  - hour: '2025-12-25T00:00:00+01:00'
    price: 0.1892
today: [0.1892, 0.1856, ...]
tomorrow: [0.2134, ...]

# Statistics
today_min: 0.1523
today_max: 0.2456
today_mean: 0.1834
tomorrow_valid: true
source_entity: sensor.epex_spot_data_market_price
```

## Example ApexCharts Card

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Electricity Prices
graph_span: 48h
span:
  start: day
series:
  - entity: sensor.ecopower_consumption_price
    name: Consumption
    data_generator: |
      return entity.attributes.data.map((entry) => {
        return [new Date(entry.start_time).getTime(), entry.price_per_kwh];
      });
  - entity: sensor.ecopower_injection_price
    name: Injection
    data_generator: |
      return entity.attributes.data.map((entry) => {
        return [new Date(entry.start_time).getTime(), entry.price_per_kwh];
      });
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.
