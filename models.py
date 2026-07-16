# models.py
# Shared data contract for Timeline Parser Mark I
# Every module in the pipeline imports from here.

from dataclasses import dataclass
from pydantic import BaseModel
from typing import List


# ── LogRecord ──────────────────────────────────────────────────────────────────
# Represents a single parsed log entry.
# One log line = one LogRecord.

@dataclass
class LogRecord:
    timestamp: str       # e.g. "Jun 16 10:21:03"
    hostname: str        # e.g. "server01"
    process: str         # e.g. "sshd", "sudo"
    pid: str             # e.g. "1234" — empty string if not present
    message: str         # e.g. "Failed password for root from 192.168.1.1"
    ip: str              # Extracted IP — empty string if not present
    user: str            # Extracted username — empty string if not present
    event_type: str      # e.g. "ssh_failed", "ssh_success", "unknown"
    raw: str             # Original unmodified log line


# ── TimelineRequest ────────────────────────────────────────────────────────────
# Pydantic model for validating the incoming POST /api/timeline request body.

class TimelineRequest(BaseModel):
    log_path: str        # e.g. "/var/log/auth.log"
    filter_key: str      # "ip", "user", or "event"
    filter_value: str    # e.g. "192.168.1.1", "root", "ssh_failed"


# ── TimelineResponse ───────────────────────────────────────────────────────────
# Pydantic model for the structured JSON response returned by POST /api/timeline.

class TimelineResponse(BaseModel):
    filter: str               # e.g. "ip=192.168.1.1"
    total_events: int         # Total matched log entries
    duration_seconds: int     # Time span from first to last event
    entities: List[str]       # Unique users or IPs observed
    timeline: List[dict]      # Ordered list of matched LogRecord objects as dicts