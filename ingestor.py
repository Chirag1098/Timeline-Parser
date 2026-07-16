# ingestor.py
# Stage 1 — Ingest
# Reads raw log file from disk and returns a clean list of log line strings.

from typing import List


def ingest(log_path: str) -> List[str]:
    """
    Reads a log file from disk and returns a clean list of raw log line strings.

    Args:
        log_path (str): Absolute or relative path to the log file.

    Returns:
        List[str]: Clean list of raw log line strings.

    Raises:
        FileNotFoundError: If the log file does not exist at the given path.
        PermissionError: If the file exists but cannot be read due to permissions.
        ValueError: If the file exists but contains no readable log lines.
        RuntimeError: For any other unexpected error during file reading.
    """

    # ── Validate path is not empty ─────────────────────────────────────────────
    if not log_path or not log_path.strip():
        raise ValueError("Log file path cannot be empty.")

    # ── Attempt to read the file ───────────────────────────────────────────────
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Log file not found: '{log_path}'. "
            f"Please verify the path and try again."
        )

    except PermissionError:
        raise PermissionError(
            f"Permission denied: Cannot read '{log_path}'. "
            f"Check file permissions and try again."
        )

    except OSError as e:
        raise RuntimeError(
            f"Unexpected error while reading '{log_path}': {str(e)}"
        )

    # ── Clean lines ────────────────────────────────────────────────────────────
    # Strip whitespace and skip empty lines
    cleaned = [line.strip() for line in lines if line.strip()]

    # ── Validate file is not empty ─────────────────────────────────────────────
    if not cleaned:
        raise ValueError(
            f"Log file is empty or contains no readable lines: '{log_path}'"
        )

    return cleaned