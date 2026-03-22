# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/claude-code) when working with code in this repository.

## Project Overview

Ecopower Dynamic Prices is a Home Assistant custom integration that calculates real electricity prices for Ecopower customers in Belgium. It parses price data from existing integrations (EPEX Spot or Energi Data Service) and applies Belgian energy costs, taxes, and Ecopower-specific margins.

## Project Structure

```
custom_components/ecopower_dynamic_prices/
├── __init__.py       # Integration setup, coordinator for data updates
├── calculations.py   # Price calculation logic (consumption/injection formulas)
├── config_flow.py    # Home Assistant configuration UI flow
├── const.py          # Constants, default values, entity definitions
├── manifest.json     # Integration metadata (version, dependencies)
├── number.py         # Number entities for editable cost parameters
├── parsers.py        # Parsers for different source integrations
├── sensor.py         # Price sensor entities
└── translations/
    └── en.json       # English translations for the UI
```

## Key Concepts

- **Source sensors**: The integration reads from EPEX Spot or Energi Data Service sensors
- **Consumption price**: Market price × multiplier + taxes/fees + VAT
- **Injection price**: Market price × multiplier - deduction
- **Number entities**: Allow runtime adjustment of all cost parameters

## Development Commands

This is a Home Assistant integration with no build system. To test:

1. Copy `custom_components/ecopower_dynamic_prices/` to your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Add the integration via Settings > Devices & Services

## Code Style

- Follow Home Assistant development guidelines
- Use type hints for all function parameters and return values
- Use async/await patterns for all I/O operations
- Prefix private methods with underscore

## Git Commit Scopes

Use conventional commits with these scopes:

| Scope | Covers |
|-------|--------|
| `calc` | `calculations.py` — price calculation logic |
| `config` | `config_flow.py` — configuration UI flow |
| `const` | `const.py` — constants, defaults, entity definitions |
| `sensor` | `sensor.py` — price sensor entities |
| `number` | `number.py` — number entities for cost parameters |
| `parser` | `parsers.py` — source integration parsers |
| `i18n` | `translations/`, `strings.json` — translations |
| `init` | `__init__.py` — integration setup, coordinator |
| `docs` | `README.md`, `images/` — documentation |
| `ci` | `.github/workflows/` — CI/CD |
| `claude` | `.claude/` — Claude Code configuration |

Omit the scope for changes spanning multiple components.
