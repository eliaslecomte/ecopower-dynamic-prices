"""Parsers for different energy price data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DATA,
    ATTR_END_TIME,
    ATTR_HOUR,
    ATTR_PRICE,
    ATTR_PRICE_PER_KWH,
    ATTR_RAW_TODAY,
    ATTR_RAW_TOMORROW,
    ATTR_START_TIME,
    ATTR_TOMORROW_VALID,
    SOURCE_TYPE_ENERGI_DATA_SERVICE,
    SOURCE_TYPE_EPEX_SPOT,
)


@dataclass
class PriceEntry:
    """A single price entry with time range and price."""

    start_time: datetime
    end_time: datetime
    price: float


@dataclass
class ParsedPriceData:
    """Parsed price data from a source sensor."""

    today: list[PriceEntry] = field(default_factory=list)
    tomorrow: list[PriceEntry] = field(default_factory=list)
    current_price: float | None = None
    tomorrow_valid: bool = False


class SourceParser(ABC):
    """Abstract base class for source sensor parsers."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier."""

    @abstractmethod
    def can_parse(self, attributes: dict[str, Any]) -> bool:
        """Check if this parser can handle the given attributes."""

    @abstractmethod
    def parse_prices(self, attributes: dict[str, Any]) -> ParsedPriceData:
        """Parse price data from sensor attributes."""

    def _parse_datetime(self, value: str | datetime) -> datetime:
        """Parse a datetime from string or return as-is if already datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise ValueError(f"Cannot parse datetime from {type(value)}: {value}")


class EpexSpotParser(SourceParser):
    """Parser for EPEX Spot sensor attributes.

    Expected format:
    attributes:
      data:
        - start_time: '2025-12-25T00:00:00+01:00'
          end_time: '2025-12-25T00:15:00+01:00'
          price_per_kwh: 0.05678
    """

    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return SOURCE_TYPE_EPEX_SPOT

    def can_parse(self, attributes: dict[str, Any]) -> bool:
        """Check if this parser can handle the given attributes."""
        if ATTR_DATA not in attributes:
            return False

        data = attributes[ATTR_DATA]
        if not isinstance(data, list) or len(data) == 0:
            return False

        # Check first entry has required fields
        first_entry = data[0]
        if not isinstance(first_entry, dict):
            return False

        return all(
            key in first_entry
            for key in [ATTR_START_TIME, ATTR_END_TIME, ATTR_PRICE_PER_KWH]
        )

    def parse_prices(self, attributes: dict[str, Any]) -> ParsedPriceData:
        """Parse price data from EPEX Spot sensor attributes."""
        data = attributes.get(ATTR_DATA, [])
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start.replace(day=today_start.day + 1)

        today_entries: list[PriceEntry] = []
        tomorrow_entries: list[PriceEntry] = []
        current_price: float | None = None

        for entry in data:
            try:
                start_time = self._parse_datetime(entry[ATTR_START_TIME])
                end_time = self._parse_datetime(entry[ATTR_END_TIME])
                price = float(entry[ATTR_PRICE_PER_KWH])

                price_entry = PriceEntry(
                    start_time=start_time,
                    end_time=end_time,
                    price=price,
                )

                # Determine if entry is for today or tomorrow
                if start_time.date() == today_start.date():
                    today_entries.append(price_entry)
                elif start_time.date() == tomorrow_start.date():
                    tomorrow_entries.append(price_entry)

                # Check if this is the current price
                if start_time <= now < end_time:
                    current_price = price

            except (KeyError, ValueError, TypeError):
                continue

        # Sort entries by start time
        today_entries.sort(key=lambda x: x.start_time)
        tomorrow_entries.sort(key=lambda x: x.start_time)

        return ParsedPriceData(
            today=today_entries,
            tomorrow=tomorrow_entries,
            current_price=current_price,
            tomorrow_valid=len(tomorrow_entries) > 0,
        )


class EnergiDataServiceParser(SourceParser):
    """Parser for Energi Data Service sensor attributes.

    Expected format:
    attributes:
      raw_today:
        - hour: '2025-12-25T00:00:00+01:00'
          price: 0.0568
      raw_tomorrow:
        - hour: '2025-12-26T00:00:00+01:00'
          price: 0.1065
      tomorrow_valid: true
    """

    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return SOURCE_TYPE_ENERGI_DATA_SERVICE

    def can_parse(self, attributes: dict[str, Any]) -> bool:
        """Check if this parser can handle the given attributes."""
        if ATTR_RAW_TODAY not in attributes:
            return False

        raw_today = attributes[ATTR_RAW_TODAY]
        if not isinstance(raw_today, list) or len(raw_today) == 0:
            return False

        # Check first entry has required fields
        first_entry = raw_today[0]
        if not isinstance(first_entry, dict):
            return False

        return ATTR_HOUR in first_entry and ATTR_PRICE in first_entry

    def parse_prices(self, attributes: dict[str, Any]) -> ParsedPriceData:
        """Parse price data from Energi Data Service sensor attributes."""
        raw_today = attributes.get(ATTR_RAW_TODAY, [])
        raw_tomorrow = attributes.get(ATTR_RAW_TOMORROW, [])
        tomorrow_valid = attributes.get(ATTR_TOMORROW_VALID, False)

        now = dt_util.now()
        today_entries: list[PriceEntry] = []
        tomorrow_entries: list[PriceEntry] = []
        current_price: float | None = None

        # Parse today's entries
        for i, entry in enumerate(raw_today):
            try:
                start_time = self._parse_datetime(entry[ATTR_HOUR])
                price = float(entry[ATTR_PRICE])

                # Determine end time from next entry or assume 15/60 min intervals
                if i + 1 < len(raw_today):
                    next_start = self._parse_datetime(raw_today[i + 1][ATTR_HOUR])
                    end_time = next_start
                else:
                    # Assume same duration as previous interval or 1 hour
                    if i > 0:
                        prev_start = self._parse_datetime(raw_today[i - 1][ATTR_HOUR])
                        duration = start_time - prev_start
                        end_time = start_time + duration
                    else:
                        end_time = start_time.replace(
                            hour=start_time.hour + 1
                            if start_time.hour < 23
                            else 0
                        )

                price_entry = PriceEntry(
                    start_time=start_time,
                    end_time=end_time,
                    price=price,
                )
                today_entries.append(price_entry)

                # Check if this is the current price
                if start_time <= now < end_time:
                    current_price = price

            except (KeyError, ValueError, TypeError):
                continue

        # Parse tomorrow's entries
        for i, entry in enumerate(raw_tomorrow):
            try:
                start_time = self._parse_datetime(entry[ATTR_HOUR])
                price = float(entry[ATTR_PRICE])

                # Determine end time from next entry
                if i + 1 < len(raw_tomorrow):
                    next_start = self._parse_datetime(raw_tomorrow[i + 1][ATTR_HOUR])
                    end_time = next_start
                else:
                    # Use same duration as today's entries or 1 hour
                    if today_entries and len(today_entries) > 1:
                        duration = today_entries[1].start_time - today_entries[0].start_time
                        end_time = start_time + duration
                    else:
                        end_time = start_time.replace(
                            hour=start_time.hour + 1
                            if start_time.hour < 23
                            else 0
                        )

                price_entry = PriceEntry(
                    start_time=start_time,
                    end_time=end_time,
                    price=price,
                )
                tomorrow_entries.append(price_entry)

            except (KeyError, ValueError, TypeError):
                continue

        # Sort entries by start time
        today_entries.sort(key=lambda x: x.start_time)
        tomorrow_entries.sort(key=lambda x: x.start_time)

        return ParsedPriceData(
            today=today_entries,
            tomorrow=tomorrow_entries,
            current_price=current_price,
            tomorrow_valid=tomorrow_valid and len(tomorrow_entries) > 0,
        )


# Registry of available parsers
PARSERS: list[SourceParser] = [
    EpexSpotParser(),
    EnergiDataServiceParser(),
]


def get_parser_for_attributes(attributes: dict[str, Any]) -> SourceParser | None:
    """Find a parser that can handle the given attributes."""
    for parser in PARSERS:
        if parser.can_parse(attributes):
            return parser
    return None


def get_parser_by_type(source_type: str) -> SourceParser | None:
    """Get a parser by its source type identifier."""
    for parser in PARSERS:
        if parser.source_type == source_type:
            return parser
    return None
