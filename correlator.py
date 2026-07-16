# correlator.py
# Stage 3 — Correlate
# Filters and sorts LogRecord objects based on a user-provided investigative lead.

from datetime import datetime
from typing import List
from models import LogRecord


# ── Accepted Filter Keys ────────────────────────────────────────────────────────
# Maps the API's filter_key to the actual LogRecord attribute name.

VALID_FILTER_KEYS = {
    "ip": "ip",
    "user": "user",
    "event": "event_type"
}


# ── Timestamp Parsing Helper ────────────────────────────────────────────────────

def _parse_timestamp(timestamp: str) -> datetime:
    """
    Parses a Syslog-style timestamp string into a datetime object for sorting.

    Args:
        timestamp (str): Syslog timestamp e.g. "Jun 16 10:21:03"

    Returns:
        datetime: Parsed datetime object. Defaults to datetime.min if parsing fails.
    """
    try:
        # Syslog timestamps have no year, so Python defaults to 1900 internally.
        # That's fine — we only care about relative order within the same file.
        return datetime.strptime(timestamp, "%b %d %H:%M:%S")
    except (ValueError, TypeError):
        # If parsing fails, treat as earliest possible time rather than crashing.
        return datetime.min


# ── Main Correlate Function ─────────────────────────────────────────────────────

def correlate(records: List[LogRecord], filter_key: str, filter_value: str) -> List[LogRecord]:
    """
    Filters LogRecord objects by a given key/value pair and sorts them chronologically.

    Args:
        records (List[LogRecord]): Structured log records from parser.py.
        filter_key (str): One of "ip", "user", or "event".
        filter_value (str): The value to match against.

    Returns:
        List[LogRecord]: Filtered and chronologically sorted records. Empty list if no matches.

    Raises:
        TypeError: If records is not a list.
        ValueError: If records is empty, filter_key is invalid, or filter_value is empty.
    """

    # ── Input Validation ───────────────────────────────────────────────────────
    if not isinstance(records, list):
        raise TypeError(
            f"Expected a list of LogRecord objects, got {type(records).__name__} instead."
        )

    if not records:
        raise ValueError(
            "No records received. The parser may have returned an empty result."
        )

    if not filter_key or filter_key not in VALID_FILTER_KEYS:
        raise ValueError(
            f"Invalid filter_key: '{filter_key}'. "
            f"Accepted values are: {list(VALID_FILTER_KEYS.keys())}"
        )

    if not filter_value or not filter_value.strip():
        raise ValueError("filter_value cannot be empty.")

    # ── Filter Records ─────────────────────────────────────────────────────────
    attribute = VALID_FILTER_KEYS[filter_key]
    matched = []

    for record in records:
        record_value = getattr(record, attribute, "")
        if record_value.lower() == filter_value.lower():
            matched.append(record)

    # ── Handle No Matches ──────────────────────────────────────────────────────
    if not matched:
        print(
            f"[CORRELATOR WARNING] No records matched filter "
            f"{filter_key}={filter_value}. Returning empty timeline."
        )
        return []

    # ── Sort Chronologically ───────────────────────────────────────────────────
    matched.sort(key=lambda r: _parse_timestamp(r.timestamp))

    print(f"[CORRELATOR] {len(matched)} record(s) matched filter {filter_key}={filter_value}.")

    return matched