from unittest.mock import patch

import pytest

import ingestor


# ── Success Path ────────────────────────────────────────────────────────────

def test_ingest_returns_cleaned_lines(tmp_path):
    """Valid file with content and blank lines -> blank lines stripped, content preserved."""
    log_file = tmp_path / "sample.log"
    log_file.write_text(
        "Jun 16 10:21:03 host sshd[123]: Failed password for root\n"
        "\n"
        "Jun 16 10:21:05 host sshd[123]: Accepted password for root\n"
        "   \n"
    )

    result = ingestor.ingest(str(log_file))

    assert result == [
        "Jun 16 10:21:03 host sshd[123]: Failed password for root",
        "Jun 16 10:21:05 host sshd[123]: Accepted password for root",
    ]


def test_ingest_strips_windows_line_endings(tmp_path):
    """File written with \\r\\n endings -> no stray \\r characters, content matches exactly."""
    log_file = tmp_path / "windows_style.log"
    log_file.write_bytes(
        b"Jun 16 10:21:03 host sshd[123]: Failed password for root\r\n"
        b"Jun 16 10:21:05 host sshd[123]: Accepted password for root\r\n"
    )

    result = ingestor.ingest(str(log_file))

    assert result == [
        "Jun 16 10:21:03 host sshd[123]: Failed password for root",
        "Jun 16 10:21:05 host sshd[123]: Accepted password for root",
    ]
    for line in result:
        assert "\r" not in line


# ── Invalid Input ─────────────────────────────────────────────────────────────

def test_ingest_empty_path_raises_valueerror():
    """Empty string path -> ValueError, before any file I/O is attempted."""
    with pytest.raises(ValueError):
        ingestor.ingest("")


def test_ingest_whitespace_path_raises_valueerror():
    """Whitespace-only path -> ValueError, same as an empty string."""
    with pytest.raises(ValueError):
        ingestor.ingest("   ")


# ── File System Failures ───────────────────────────────────────────────────────

def test_ingest_missing_file_raises_filenotfounderror(tmp_path):
    """Path pointing to a file that doesn't exist -> FileNotFoundError, path included in message."""
    missing_path = str(tmp_path / "does_not_exist.log")

    with pytest.raises(FileNotFoundError) as exc_info:
        ingestor.ingest(missing_path)

    assert missing_path in str(exc_info.value)


def test_ingest_permission_denied_raises_permissionerror(tmp_path):
    """open() raising PermissionError -> wrapped and re-raised as PermissionError with a clear message."""
    log_file = tmp_path / "locked.log"
    log_file.write_text("Jun 16 10:21:03 host sshd[123]: some event\n")

    with patch("builtins.open", side_effect=PermissionError("Simulated permission denial")):
        with pytest.raises(PermissionError) as exc_info:
            ingestor.ingest(str(log_file))

    assert str(log_file) in str(exc_info.value)


def test_ingest_generic_oserror_raises_runtimeerror(tmp_path):
    """A low-level OSError that isn't FileNotFoundError/PermissionError -> wrapped as RuntimeError."""
    log_file = tmp_path / "sample.log"
    log_file.write_text("some content\n")

    with patch("builtins.open", side_effect=OSError("Simulated disk failure")):
        with pytest.raises(RuntimeError) as exc_info:
            ingestor.ingest(str(log_file))

    assert "Simulated disk failure" in str(exc_info.value)


# ── Empty Content ───────────────────────────────────────────────────────────

def test_ingest_empty_file_raises_valueerror(tmp_path):
    """0-byte file -> ValueError, readlines() returns an empty list directly."""
    log_file = tmp_path / "empty.log"
    log_file.write_text("")

    with pytest.raises(ValueError):
        ingestor.ingest(str(log_file))


def test_ingest_blank_lines_only_raises_valueerror(tmp_path):
    """File containing only blank/whitespace lines -> ValueError, list comprehension filters everything out."""
    log_file = tmp_path / "blank_lines.log"
    log_file.write_text("\n\n   \n\n\t\n")

    with pytest.raises(ValueError):
        ingestor.ingest(str(log_file))