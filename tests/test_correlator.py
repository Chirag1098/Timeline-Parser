from datetime import datetime

import pytest

import correlator
from models import LogRecord


# ── Factory Fixture ─────────────────────────────────────────────────────────────

@pytest.fixture
def make_record():
    """Builds a LogRecord with sensible defaults; override only the fields a test cares about."""
    def _make(timestamp="Jun 16 10:21:03", hostname="webserver01", process="sshd",
              pid="1234", message="some message", ip="192.168.1.1", user="root",
              event_type="ssh_failed", raw="raw line"):
        return LogRecord(timestamp=timestamp, hostname=hostname, process=process, pid=pid,
                          message=message, ip=ip, user=user, event_type=event_type, raw=raw)
    return _make


# ── Input Validation ──────────────────────────────────────────────────────────

def test_correlate_raises_typeerror_for_non_list_records():
    """records is a string instead of a list -> TypeError."""
    with pytest.raises(TypeError):
        correlator.correlate("not a list", "ip", "192.168.1.1")


def test_correlate_raises_valueerror_for_empty_records():
    """records is an empty list -> ValueError."""
    with pytest.raises(ValueError):
        correlator.correlate([], "ip", "192.168.1.1")


def test_correlate_raises_valueerror_for_invalid_filter_key(make_record):
    """filter_key is not one of ip/user/event -> ValueError."""
    records = [make_record()]

    with pytest.raises(ValueError):
        correlator.correlate(records, "bogus", "root")


def test_correlate_raises_valueerror_for_empty_filter_key(make_record):
    """filter_key is an empty string -> ValueError."""
    records = [make_record()]

    with pytest.raises(ValueError):
        correlator.correlate(records, "", "root")


def test_correlate_raises_valueerror_for_empty_filter_value(make_record):
    """filter_value is an empty string -> ValueError."""
    records = [make_record()]

    with pytest.raises(ValueError):
        correlator.correlate(records, "user", "")


def test_correlate_raises_valueerror_for_whitespace_filter_value(make_record):
    """filter_value is whitespace only -> ValueError."""
    records = [make_record()]

    with pytest.raises(ValueError):
        correlator.correlate(records, "user", "   ")


# ── Filtering Logic ────────────────────────────────────────────────────────────

def test_correlate_filters_by_ip(make_record):
    """filter_key='ip' -> only records with a matching ip are returned."""
    records = [
        make_record(ip="192.168.1.105", timestamp="Jun 16 10:21:03"),
        make_record(ip="10.0.0.1", timestamp="Jun 16 10:22:00"),
        make_record(ip="192.168.1.105", timestamp="Jun 16 10:23:00"),
    ]

    result = correlator.correlate(records, "ip", "192.168.1.105")

    assert len(result) == 2
    assert all(r.ip == "192.168.1.105" for r in result)


def test_correlate_filters_by_user(make_record):
    """filter_key='user' -> only records with a matching user are returned."""
    records = [
        make_record(user="root", timestamp="Jun 16 10:21:03"),
        make_record(user="admin", timestamp="Jun 16 10:22:00"),
        make_record(user="root", timestamp="Jun 16 10:23:00"),
    ]

    result = correlator.correlate(records, "user", "root")

    assert len(result) == 2
    assert all(r.user == "root" for r in result)


def test_correlate_filters_by_event(make_record):
    """filter_key='event' -> filters on record.event_type, proving the name mapping is correct."""
    records = [
        make_record(event_type="ssh_failed", timestamp="Jun 16 10:21:03"),
        make_record(event_type="ssh_success", timestamp="Jun 16 10:22:00"),
        make_record(event_type="ssh_failed", timestamp="Jun 16 10:23:00"),
    ]

    result = correlator.correlate(records, "event", "ssh_failed")

    assert len(result) == 2
    assert all(r.event_type == "ssh_failed" for r in result)


# ── Case Insensitivity ────────────────────────────────────────────────────────

def test_correlate_matching_is_case_insensitive(make_record):
    """filter_value in a different case than the stored value -> still matches."""
    records = [make_record(user="root")]

    result = correlator.correlate(records, "user", "ROOT")

    assert len(result) == 1


# ── No Matches ─────────────────────────────────────────────────────────────────

def test_correlate_returns_empty_list_when_no_matches(make_record):
    """Filter matches nothing -> empty list, not an exception."""
    records = [make_record(ip="192.168.1.1")]

    result = correlator.correlate(records, "ip", "10.0.0.99")

    assert result == []


# ── Sorting ────────────────────────────────────────────────────────────────────

def test_correlate_sorts_matched_records_chronologically(make_record):
    """Matching records passed in out of order -> returned in chronological order."""
    records = [
        make_record(ip="1.2.3.4", timestamp="Jun 16 11:00:00"),
        make_record(ip="1.2.3.4", timestamp="Jun 16 09:00:00"),
        make_record(ip="1.2.3.4", timestamp="Jun 16 10:00:00"),
    ]

    result = correlator.correlate(records, "ip", "1.2.3.4")

    assert [r.timestamp for r in result] == [
        "Jun 16 09:00:00",
        "Jun 16 10:00:00",
        "Jun 16 11:00:00",
    ]


def test_correlate_handles_unparseable_timestamp_without_crashing(make_record):
    """One matching record has a garbage timestamp -> sort still completes, doesn't crash."""
    records = [
        make_record(ip="1.2.3.4", timestamp="not a real timestamp"),
        make_record(ip="1.2.3.4", timestamp="Jun 16 10:00:00"),
    ]

    result = correlator.correlate(records, "ip", "1.2.3.4")

    assert len(result) == 2
    # The unparseable timestamp falls back to datetime.min, so it sorts first.
    assert result[0].timestamp == "not a real timestamp"
    assert result[1].timestamp == "Jun 16 10:00:00"


# ── _parse_timestamp() ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("timestamp_str, should_be_min", [
    ("Jun 16 10:21:03", False),
    ("not a timestamp", True),
    ("", True),
])
def test_parse_timestamp_handles_valid_and_invalid_input(timestamp_str, should_be_min):
    """Valid timestamps parse correctly; anything unparseable falls back to datetime.min."""
    result = correlator._parse_timestamp(timestamp_str)

    if should_be_min:
        assert result == datetime.min
    else:
        assert result == datetime(1900, 6, 16, 10, 21, 3)