# parser.py
# Stage 2 — Parse
# Converts raw log line strings into structured LogRecord objects.

import re
from typing import List
from models import LogRecord


# ── Regex Patterns ─────────────────────────────────────────────────────────────

# Core Syslog line pattern
SYSLOG_PATTERN = re.compile(
    r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'  # timestamp
    r'(\S+)\s+'                                       # hostname
    r'(\w[\w\-]*)(?:\[(\d+)\])?:\s+'                 # process[pid]
    r'(.*)$'                                          # message
)

# IP address extraction pattern
IP_PATTERN = re.compile(
    r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
)

# Username extraction pattern
FOR_USER_PATTERN = re.compile(r'for\s+user\s+(\w+)', re.IGNORECASE)   # "session opened for user deploy"
USER_EQUALS_PATTERN = re.compile(r'USER=(\w+)', re.IGNORECASE)         # "USER=admin" (sudo/cron)
FOR_PATTERN = re.compile(r'for\s+(\w+)', re.IGNORECASE)                # "Failed password for root"
USER_KEYWORD_PATTERN = re.compile(r'user\s+(\w+)', re.IGNORECASE)      # "switched user root"


# ── Event Type Classification ──────────────────────────────────────────────────

def _classify_event(message: str) -> str:
    """
    Classifies the event type based on keywords found in the message.

    Args:
        message (str): The message field extracted from the log line.

    Returns:
        str: A classified event type string.
    """
    message_lower = message.lower()

    if any(k in message_lower for k in ["failed password", "authentication failure", "invalid user"]):
        return "ssh_failed"

    elif any(k in message_lower for k in ["accepted password", "accepted publickey", "session opened"]):
        return "ssh_success"

    elif any(k in message_lower for k in ["disconnected", "session closed", "session opened"]):
        return "ssh_disconnect"

    elif any(k in message_lower for k in ["command", "sudo"]):
        return "sudo_command"

    elif any(k in message_lower for k in ["connection", "connecting"]):
        return "ssh_attempt"

    return "unknown"


def _extract_user(message: str) -> str:
    for pattern in (FOR_USER_PATTERN, USER_EQUALS_PATTERN, FOR_PATTERN, USER_KEYWORD_PATTERN):
        match = pattern.search(message)
        if match:
            return match.group(1)
    return ""

# ── Main Parse Function ────────────────────────────────────────────────────────

def parse(raw_lines: List[str]) -> List[LogRecord]:
    """
    Parses a list of raw Syslog line strings into structured LogRecord objects.

    Args:
        raw_lines (List[str]): Raw log line strings from ingestor.py.

    Returns:
        List[LogRecord]: List of structured LogRecord objects.

    Raises:
        TypeError: If raw_lines is not a list.
        ValueError: If raw_lines is empty, or if no lines could be parsed.
    """

    # ── Input Validation ───────────────────────────────────────────────────────
    if not isinstance(raw_lines, list):
        raise TypeError(
            f"Expected a list of strings, got {type(raw_lines).__name__} instead."
        )

    if not raw_lines:
        raise ValueError(
            "No log lines received. The ingestor may have returned an empty result."
        )

    # ── Parse Each Line ────────────────────────────────────────────────────────
    records = []
    skipped = 0

    for line in raw_lines:

        # Skip non-string entries defensively
        if not isinstance(line, str):
            print(f"[PARSER WARNING] Skipping non-string entry: {repr(line)}")
            skipped += 1
            continue

        # Match line against Syslog pattern
        match = SYSLOG_PATTERN.match(line)

        if not match:
            print(f"[PARSER WARNING] Line did not match Syslog pattern, skipping: {line[:80]}")
            skipped += 1
            continue

        # Extract core fields
        timestamp = match.group(1).strip()
        hostname  = match.group(2).strip()
        process   = match.group(3).strip()
        pid       = match.group(4) or ""
        message   = match.group(5).strip()

        # Extract IP address from message
        ip_match = IP_PATTERN.search(message)
        ip = ip_match.group(0) if ip_match else ""

        # Extract username from message
        user = _extract_user(message)

        # Classify event type
        event_type = _classify_event(message)

        # Construct LogRecord
        record = LogRecord(
            timestamp  = timestamp,
            hostname   = hostname,
            process    = process,
            pid        = pid,
            message    = message,
            ip         = ip,
            user       = user,
            event_type = event_type,
            raw        = line
        )

        records.append(record)

    # ── Validate Results ───────────────────────────────────────────────────────
    if not records:
        raise ValueError(
            f"No log lines could be parsed. "
            f"All {skipped} line(s) were skipped. "
            f"Verify the log file is in standard Syslog format."
        )

    print(f"[PARSER] Successfully parsed {len(records)} line(s). Skipped {skipped} line(s).")

    return records