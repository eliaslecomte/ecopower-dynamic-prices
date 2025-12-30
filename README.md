# Ecopower Dynamic Prices

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant integration that calculates real electricity prices for Ecopower customers in Belgium, including all taxes, fees, and supplier margins.

## Features

- **Parses existing price sensors** from EPEX Spot or Energi Data Service integrations
- **Calculates consumption prices** with all Belgian energy costs and Ecopower margins
- **Calculates injection prices** with Ecopower deductions
- **Editable cost parameters** via number entities - change values at runtime
- **Full price arrays** in sensor attributes for easy charting with ApexCharts
- **Multiple instances** supported - track different source sensors with separate configurations

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

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Ecopower Dynamic Prices"
4. Select your source sensor (from EPEX Spot or Energi Data Service)
5. Configure cost parameters (defaults are provided for Ecopower Belgium)

The integration will create a device named based on your source sensor, e.g., "Ecopower (Epex Spot)" or "Ecopower (Energi Data Service Total Price)".

## Supported Source Integrations

- [EPEX Spot](https://github.com/mampfes/ha_epex_spot)
- [Energi Data Service](https://github.com/MTrab/energidataservice)

## Entities Created

Entity IDs are automatically generated based on the source sensor name. For example, if your source sensor is `sensor.epex_spot_be_price`, entities will be named like `sensor.ecopower_epex_spot_be_price_consumption_price`.

### Sensors

| Entity | Description |
| ------ | ----------- |
| `sensor.<name>_consumption_price` | Current consumption price with all costs |
| `sensor.<name>_injection_price` | Current injection price with deductions |

### Number Entities (Editable)

All cost parameters can be adjusted at runtime via number entities.

**Ecopower-specific:**

| Entity | Default | Description |
| ------ | ------- | ----------- |
| `number.<name>_consumption_multiplier` | 1.02 | Ecopower margin on market price |
| `number.<name>_ecopower_tariff` | 0.004 €/kWh | Ecopower administrative cost |
| `number.<name>_injection_multiplier` | 0.98 | Ecopower margin on injection |
| `number.<name>_injection_deduction` | 0.015 €/kWh | Ecopower injection fee |

**Belgian Energy Costs:**

| Entity | Default | Description |
| ------ | ------- | ----------- |
| `number.<name>_gsc_groene_stroom` | 0.011 €/kWh | Green electricity certificates |
| `number.<name>_wkk` | 0.0039 €/kWh | CHP certificates |
| `number.<name>_afname_tarief` | 0.0589 €/kWh | Distribution network tariff |
| `number.<name>_bijdrage_energie` | 0.0019 €/kWh | Energy contribution fee |
| `number.<name>_bijzondere_accijns` | 0.0475 €/kWh | Special excise tax |
| `number.<name>_btw_vat_rate` | 6 % | VAT percentage |

## Price Formulas

### Consumption Price

```text
((market_price * consumption_multiplier) + all_costs) * (1 + vat_rate / 100)
```

Where `all_costs` = supplier_cost + green_certificates + chp_certificates + distribution_cost + energy_contribution + excise_tax

### Injection Price

```text
(market_price * injection_multiplier) - injection_deduction
```

## Sensor Attributes

Both sensors include rich attributes for charting:

```yaml
# Detailed format (like EPEX Spot)
data:
  - start_time: '2025-12-25T00:00:00+01:00'
    end_time: '2025-12-25T01:00:00+01:00'
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
tomorrow_min: 0.1456
tomorrow_max: 0.2234
tomorrow_mean: 0.1756
tomorrow_valid: true
source_entity: sensor.epex_spot_be_price
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
  - entity: sensor.ecopower_epex_spot_consumption_price
    name: Consumption
    data_generator: |
      return entity.attributes.data.map((entry) => {
        return [new Date(entry.start_time).getTime(), entry.price_per_kwh];
      });
  - entity: sensor.ecopower_epex_spot_injection_price
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
