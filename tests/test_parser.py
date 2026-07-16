import pytest

import parser


# ── Input Validation ──────────────────────────────────────────────────────────

def test_parse_raises_typeerror_for_non_list_input():
    """A string instead of a list -> TypeError, since parse() expects List[str]."""
    with pytest.raises(TypeError):
        parser.parse("not a list")


def test_parse_raises_valueerror_for_empty_list():
    """An empty list -> ValueError, nothing to parse."""
    with pytest.raises(ValueError):
        parser.parse([])


# ── Well-Formed Line Parsing ────────────────────────────────────────────────────

def test_parse_extracts_all_fields_from_valid_line():
    """A complete, realistic syslog line with a [pid] -> every field extracted correctly."""
    line = "Jun 16 10:21:03 webserver01 sshd[1234]: Failed password for root from 192.168.1.105 port 51344 ssh2"

    result = parser.parse([line])

    assert len(result) == 1
    record = result[0]
    assert record.timestamp == "Jun 16 10:21:03"
    assert record.hostname == "webserver01"
    assert record.process == "sshd"
    assert record.pid == "1234"
    assert record.message == "Failed password for root from 192.168.1.105 port 51344 ssh2"
    assert record.ip == "192.168.1.105"
    assert record.user == "root"
    assert record.event_type == "ssh_failed"


def test_parse_handles_line_without_pid():
    """A line with no [pid] bracket (e.g. kernel messages) -> pid is empty, nothing crashes."""
    line = "Jun 16 09:15:33 webserver01 kernel: eth0: link up, 1000 Mbps, full duplex"

    result = parser.parse([line])

    assert len(result) == 1
    assert result[0].pid == ""
    assert result[0].process == "kernel"


def test_parse_preserves_raw_original_line():
    """record.raw must match the original input string exactly, unmodified."""
    line = "Jun 16 10:21:03 webserver01 sshd[1234]: Failed password for root"

    result = parser.parse([line])

    assert result[0].raw == line


def test_parse_returns_multiple_records_in_order():
    """Three valid lines -> three records, in the same order as input."""
    lines = [
        "Jun 16 10:21:03 webserver01 sshd[1234]: Failed password for root",
        "Jun 16 10:21:20 webserver01 sshd[1256]: Accepted password for root",
        "Jun 16 10:22:10 webserver01 sshd[1256]: Disconnected",
    ]

    result = parser.parse(lines)

    assert len(result) == 3
    assert result[0].event_type == "ssh_failed"
    assert result[1].event_type == "ssh_success"
    assert result[2].event_type == "ssh_disconnect"


# ── Malformed Line Handling ───────────────────────────────────────────────────

def test_parse_skips_line_that_does_not_match_syslog_pattern():
    """A garbage line mixed with a valid one -> garbage skipped, valid line still parsed."""
    lines = [
        "this is not a syslog line at all",
        "Jun 16 10:21:03 webserver01 sshd[1234]: Failed password for root",
    ]

    result = parser.parse(lines)

    assert len(result) == 1
    assert result[0].process == "sshd"


def test_parse_skips_non_string_entries():
    """A non-string item mixed into the list -> skipped, valid entries still processed."""
    lines = [
        12345,
        "Jun 16 10:21:03 webserver01 sshd[1234]: Failed password for root",
    ]

    result = parser.parse(lines)

    assert len(result) == 1
    assert result[0].process == "sshd"


def test_parse_raises_valueerror_when_all_lines_fail_to_parse():
    """Every line malformed -> ValueError, since zero records could be built."""
    lines = ["garbage one", "garbage two", "not a syslog line"]

    with pytest.raises(ValueError):
        parser.parse(lines)


# ── IP Extraction ──────────────────────────────────────────────────────────────

def test_parse_extracts_ip_when_present():
    """Message containing a dotted IPv4 address -> record.ip matches exactly."""
    line = "Jun 16 10:25:00 webserver01 sshd[1401]: Connection from 192.168.1.77 port 43210"

    result = parser.parse([line])

    assert result[0].ip == "192.168.1.77"


def test_parse_ip_is_empty_when_absent():
    """Message with no IP address -> record.ip is empty string."""
    line = "Jun 16 11:15:00 webserver01 CRON[1600]: (root) CMD (run-parts /etc/cron.hourly)"

    result = parser.parse([line])

    assert result[0].ip == ""


# ── Username Extraction ────────────────────────────────────────────────────────

@pytest.mark.parametrize("message, expected_user", [
    ("Failed password for root from 1.2.3.4", "root"),
    ("session opened for user deploy by (uid=0)", "deploy"),
    ("switched user root successfully", "root"),
    ("root : TTY=pts/0 ; USER=admin ; COMMAND=/bin/bash", "admin"),
    ("Disconnected from 1.2.3.4 port 51360", ""),
])
def test_extract_user_handles_all_patterns(message, expected_user):
    """_extract_user() must try patterns in priority order -- most specific first."""
    assert parser._extract_user(message) == expected_user


# ── Event Classification ────────────────────────────────────────────────────────

@pytest.mark.parametrize("message, expected_event_type", [
    ("Failed password for root", "ssh_failed"),
    ("authentication failure for user", "ssh_failed"),
    ("Invalid user admin from 1.2.3.4", "ssh_failed"),
    ("Accepted password for root", "ssh_success"),
    ("Accepted publickey for deploy", "ssh_success"),
    ("session opened for user root", "ssh_success"),
    ("Disconnected from 1.2.3.4", "ssh_disconnect"),
    ("session closed for user root", "ssh_disconnect"),
    ("root : COMMAND=/bin/bash", "sudo_command"),
    ("someone ran sudo", "sudo_command"),
    ("Connection from 1.2.3.4 port 22", "ssh_attempt"),
    ("connecting to host", "ssh_attempt"),
    ("some unrelated system message", "unknown"),
])
def test_classify_event_maps_keywords_correctly(message, expected_event_type):
    """_classify_event() must map each keyword to its correct category, first match wins."""
    assert parser._classify_event(message) == expected_event_type