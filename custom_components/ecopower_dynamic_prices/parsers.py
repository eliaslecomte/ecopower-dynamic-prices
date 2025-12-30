"""Parsers for different energy price data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
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

_LOGGER = logging.getLogger(__name__)


def _is_list_like(value: Any) -> bool:
    """Check if value is list-like (list or tuple)."""
    return isinstance(value, (list, tuple))


def _is_dict_like(value: Any) -> bool:
    """Check if value is dict-like (has keys method)."""
    return isinstance(value, dict) or hasattr(value, "keys")


def _has_array_with_keys(
    attributes: dict[str, Any], array_key: str, required_keys: list[str]
) -> bool:
    """Check if attributes has an array at array_key with entries containing required_keys.

    This is the core shape detection logic. It checks:
    1. The array_key exists in attributes
    2. The value is a non-empty list/tuple
    3. The first entry is dict-like
    4. The first entry contains all required_keys
    """
    # Check array exists
    if array_key not in attributes:
        return False

    array = attributes[array_key]

    # Check it's a non-empty list-like
    if not _is_list_like(array) or len(array) == 0:
        return False

    # Check first entry is dict-like
    first_entry = array[0]
    if not _is_dict_like(first_entry):
        return False

    # Check all required keys exist (case-insensitive)
    for key in required_keys:
        if _find_key(first_entry, key) is None:
            return False

    return True


def analyze_sensor_shape(attributes: dict[str, Any]) -> dict[str, Any]:
    """Analyze sensor attributes and return shape information.

    Returns a dict with:
    - detected_type: 'epex_spot', 'energi_data_service', or None
    - reason: Human-readable explanation
    - details: Additional debug info
    """
    result = {
        "detected_type": None,
        "reason": "",
        "details": {},
    }

    # Shape 1: EPEX Spot format
    # - Has 'data' array with entries containing: start_time, end_time, price_per_kwh
    if _has_array_with_keys(attributes, "data", ["start_time", "end_time", "price_per_kwh"]):
        result["detected_type"] = SOURCE_TYPE_EPEX_SPOT
        result["reason"] = "Found 'data' array with start_time, end_time, price_per_kwh"
        return result

    # Also check for 'data' with just 'price' (some EPEX integrations)
    if _has_array_with_keys(attributes, "data", ["start_time", "end_time", "price"]):
        result["detected_type"] = SOURCE_TYPE_EPEX_SPOT
        result["reason"] = "Found 'data' array with start_time, end_time, price"
        return result

    # Shape 2: Energi Data Service format
    # - Has 'raw_today' array with entries containing: hour, price
    if _has_array_with_keys(attributes, "raw_today", ["hour", "price"]):
        result["detected_type"] = SOURCE_TYPE_ENERGI_DATA_SERVICE
        result["reason"] = "Found 'raw_today' array with hour, price"
        return result

    # Could not detect - provide diagnostic info
    result["reason"] = "No matching shape found"
    result["details"]["attribute_keys"] = list(attributes.keys()) if attributes else []

    # Check what's present for debugging
    if "data" in attributes:
        data = attributes["data"]
        result["details"]["data_type"] = type(data).__name__
        if _is_list_like(data) and len(data) > 0:
            first = data[0]
            result["details"]["data_first_entry_type"] = type(first).__name__
            if _is_dict_like(first):
                result["details"]["data_first_entry_keys"] = list(first.keys())

    if "raw_today" in attributes:
        raw_today = attributes["raw_today"]
        result["details"]["raw_today_type"] = type(raw_today).__name__
        if _is_list_like(raw_today) and len(raw_today) > 0:
            first = raw_today[0]
            result["details"]["raw_today_first_entry_type"] = type(first).__name__
            if _is_dict_like(first):
                result["details"]["raw_today_first_entry_keys"] = list(first.keys())

    return result


def _find_key(attributes: dict[str, Any], *possible_keys: str) -> str | None:
    """Find a key in attributes, trying multiple variations."""
    for key in possible_keys:
        if key in attributes:
            return key
        # Try case-insensitive match
        for attr_key in attributes:
            # Skip non-string keys
            if not isinstance(attr_key, str):
                continue
            if attr_key.lower() == key.lower():
                return attr_key
            # Also try with spaces replaced by underscores
            if attr_key.lower().replace(" ", "_") == key.lower():
                return attr_key
    return None


def _get_value(attributes: dict[str, Any], *possible_keys: str) -> Any | None:
    """Get a value from attributes, trying multiple key variations."""
    key = _find_key(attributes, *possible_keys)
    if key:
        return attributes[key]
    return None


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

    def _get_data_key(self, attributes: dict[str, Any]) -> str | None:
        """Find the data key in attributes."""
        return _find_key(attributes, ATTR_DATA, "Data", "data")

    def can_parse(self, attributes: dict[str, Any]) -> bool:
        """Check if this parser can handle the given attributes.

        Checks for EPEX Spot shape:
        - Has 'data' array with entries containing 'start_time', 'end_time', and 'price_per_kwh' (or 'price')
        """
        # Check for full EPEX format with price_per_kwh
        if _has_array_with_keys(attributes, "data", ["start_time", "end_time", "price_per_kwh"]):
            return True
        # Also accept format with just 'price' instead of 'price_per_kwh'
        if _has_array_with_keys(attributes, "data", ["start_time", "end_time", "price"]):
            return True
        return False

    def parse_prices(self, attributes: dict[str, Any]) -> ParsedPriceData:
        """Parse price data from EPEX Spot sensor attributes."""
        data_key = self._get_data_key(attributes)
        data = attributes.get(data_key, []) if data_key else []

        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        today_entries: list[PriceEntry] = []
        tomorrow_entries: list[PriceEntry] = []
        current_price: float | None = None

        for entry in data:
            try:
                start_key = _find_key(entry, ATTR_START_TIME, "start_time")
                end_key = _find_key(entry, ATTR_END_TIME, "end_time")
                price_key = _find_key(entry, ATTR_PRICE_PER_KWH, "price_per_kwh", "price")

                if not all([start_key, end_key, price_key]):
                    continue

                start_time = self._parse_datetime(entry[start_key])
                end_time = self._parse_datetime(entry[end_key])
                price = float(entry[price_key])

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

            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.debug("Error parsing EPEX entry: %s", err)
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

    def _get_raw_today_key(self, attributes: dict[str, Any]) -> str | None:
        """Find the raw_today key in attributes."""
        return _find_key(attributes, ATTR_RAW_TODAY, "raw_today", "Raw today", "raw today")

    def _get_raw_tomorrow_key(self, attributes: dict[str, Any]) -> str | None:
        """Find the raw_tomorrow key in attributes."""
        return _find_key(attributes, ATTR_RAW_TOMORROW, "raw_tomorrow", "Raw tomorrow", "raw tomorrow")

    def can_parse(self, attributes: dict[str, Any]) -> bool:
        """Check if this parser can handle the given attributes.

        Checks for Energi Data Service shape:
        - Has 'raw_today' array with entries containing 'hour' and 'price'
        """
        return _has_array_with_keys(attributes, "raw_today", ["hour", "price"])

    def parse_prices(self, attributes: dict[str, Any]) -> ParsedPriceData:
        """Parse price data from Energi Data Service sensor attributes."""
        raw_today_key = self._get_raw_today_key(attributes)
        raw_tomorrow_key = self._get_raw_tomorrow_key(attributes)

        raw_today = attributes.get(raw_today_key, []) if raw_today_key else []
        raw_tomorrow = attributes.get(raw_tomorrow_key, []) if raw_tomorrow_key else []

        tomorrow_valid_key = _find_key(attributes, ATTR_TOMORROW_VALID, "tomorrow_valid")
        tomorrow_valid = attributes.get(tomorrow_valid_key, False) if tomorrow_valid_key else False

        now = dt_util.now()
        today_entries: list[PriceEntry] = []
        tomorrow_entries: list[PriceEntry] = []
        current_price: float | None = None

        # Parse today's entries
        for i, entry in enumerate(raw_today):
            try:
                hour_key = _find_key(entry, ATTR_HOUR, "hour")
                price_key = _find_key(entry, ATTR_PRICE, "price")

                if not hour_key or not price_key:
                    continue

                start_time = self._parse_datetime(entry[hour_key])
                price = float(entry[price_key])

                # Determine end time from next entry or assume 15/60 min intervals
                if i + 1 < len(raw_today):
                    next_hour_key = _find_key(raw_today[i + 1], ATTR_HOUR, "hour")
                    if next_hour_key:
                        next_start = self._parse_datetime(raw_today[i + 1][next_hour_key])
                        end_time = next_start
                    else:
                        end_time = start_time + timedelta(hours=1)
                else:
                    # Assume same duration as previous interval or 1 hour
                    if i > 0:
                        prev_hour_key = _find_key(raw_today[i - 1], ATTR_HOUR, "hour")
                        if prev_hour_key:
                            prev_start = self._parse_datetime(raw_today[i - 1][prev_hour_key])
                            duration = start_time - prev_start
                            end_time = start_time + duration
                        else:
                            end_time = start_time + timedelta(hours=1)
                    else:
                        end_time = start_time + timedelta(hours=1)

                price_entry = PriceEntry(
                    start_time=start_time,
                    end_time=end_time,
                    price=price,
                )
                today_entries.append(price_entry)

                # Check if this is the current price
                if start_time <= now < end_time:
                    current_price = price

            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.debug("Error parsing Energi today entry: %s", err)
                continue

        # Parse tomorrow's entries
        for i, entry in enumerate(raw_tomorrow):
            try:
                hour_key = _find_key(entry, ATTR_HOUR, "hour")
                price_key = _find_key(entry, ATTR_PRICE, "price")

                if not hour_key or not price_key:
                    continue

                start_time = self._parse_datetime(entry[hour_key])
                price = float(entry[price_key])

                # Determine end time from next entry
                if i + 1 < len(raw_tomorrow):
                    next_hour_key = _find_key(raw_tomorrow[i + 1], ATTR_HOUR, "hour")
                    if next_hour_key:
                        next_start = self._parse_datetime(raw_tomorrow[i + 1][next_hour_key])
                        end_time = next_start
                    else:
                        end_time = start_time + timedelta(hours=1)
                else:
                    # Use same duration as today's entries or 1 hour
                    if today_entries and len(today_entries) > 1:
                        duration = today_entries[1].start_time - today_entries[0].start_time
                        end_time = start_time + duration
                    else:
                        end_time = start_time + timedelta(hours=1)

                price_entry = PriceEntry(
                    start_time=start_time,
                    end_time=end_time,
                    price=price,
                )
                tomorrow_entries.append(price_entry)

            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.debug("Error parsing Energi tomorrow entry: %s", err)
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
    """Find a parser that can handle the given attributes based on shape analysis.

    Uses analyze_sensor_shape() to detect the data format, then returns
    the appropriate parser.
    """
    shape_info = analyze_sensor_shape(attributes)
    detected_type = shape_info["detected_type"]

    _LOGGER.debug(
        "Shape analysis result: type=%s, reason=%s, details=%s",
        detected_type,
        shape_info["reason"],
        shape_info.get("details", {}),
    )

    if detected_type is None:
        return None

    return get_parser_by_type(detected_type)


def get_parser_by_type(source_type: str) -> SourceParser | None:
    """Get a parser by its source type identifier."""
    for parser in PARSERS:
        if parser.source_type == source_type:
            return parser
    return None
