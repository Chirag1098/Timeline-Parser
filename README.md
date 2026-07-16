# Timeline Parser — Mark I

> A Python/FastAPI web application that parses Linux syslog files, correlates events around a user-provided investigative lead, and renders a chronological timeline through a REST API and web interface.

---

## Overview

**Timeline Parser** helps security analysts, system administrators, and developers quickly reconstruct a sequence of events from raw system logs — without manually grepping through thousands of lines.

Give it a lead — an IP address, a username, or an event type — and it extracts every related log entry, sorts it chronologically, and renders it as a clean, visual timeline in the browser.

This is **Mark I**, the first release: a focused, fully-tested foundation built around Linux syslog.

---

## The Problem

During an incident investigation, an analyst often needs to answer questions like:

- *What did this IP address do, and in what order?*
- *When did this user account first appear, and what actions followed?*
- *What sequence of events preceded this failure?*

Answering these by hand — scrolling, grepping, mentally stitching together log lines — is slow and error-prone. Timeline Parser automates that reconstruction.

---

## How It Works

```
[ Log File ]  →  [ Ingest ]  →  [ Parse ]  →  [ Correlate ]  →  [ Timeline ]
```

1. **Ingest** — reads the syslog file from disk
2. **Parse** — extracts structured fields (timestamp, host, process, IP, user, event type) from each line
3. **Correlate** — filters to the entries matching your lead, sorted chronologically
4. **Respond** — returns a structured timeline via the API, rendered visually in the browser

---

## Features

- Syslog / Linux log parsing with structured field extraction
- Investigation by IP address, username, or event type
- Automatic chronological sorting
- REST API with auto-generated interactive documentation
- Clean web interface — no manual API calls required
- Robust error handling throughout — malformed input never crashes the app
- Zero unnecessary dependencies

---

## Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3 |
| Web Framework | FastAPI |
| Server | uvicorn |
| Frontend | Vanilla HTML / CSS / JS |
| Testing | pytest |

---

## Getting Started

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
git clone <repository-url>
cd timeline-parser-mark1

python -m venv mark1
source mark1/bin/activate      # Windows: mark1\Scripts\activate

pip install -r requirements.txt
```

### Running the Application

```bash
uvicorn main:app --reload
```

- Web UI: [http://localhost:8000](http://localhost:8000)
- Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Usage

### `POST /api/timeline`

**Request:**
```json
{
  "log_path": "logs/sample_auth.log",
  "filter_key": "ip",
  "filter_value": "192.168.1.105"
}
```

**Accepted `filter_key` values:** `ip`, `user`, `event`

**Response:**
```json
{
  "filter": "ip=192.168.1.105",
  "total_events": 7,
  "duration_seconds": 4139,
  "entities": ["192.168.1.105", "root"],
  "timeline": [ ... ]
}
```

### `GET /api/health`

Health check endpoint — confirms the service is running.

---

## Running Tests

```bash
pytest tests/ -v
```

The suite covers ingestion, parsing, and correlation — including edge cases like malformed input, missing files, and empty results.

---

## Project Structure

```
timeline-parser-mark1/
├── main.py              # FastAPI app — REST endpoints, orchestrates the pipeline
├── ingestor.py           # Reads log files from disk
├── parser.py             # Parses raw lines into structured records
├── correlator.py         # Filters and sorts by investigative lead
├── models.py             # Shared data models
├── static/
│   └── index.html        # Web interface
├── logs/                 # Sample log files for testing
├── tests/                # Automated test suite
└── requirements.txt
```

---

## Roadmap

Mark I is complete and fully tested. Planned for future releases:

- Auto-correlation (no filter required)
- Windows Event Log support
- Multi-file log ingestion
- Expanded event classification

---

## Part of a Larger Suite

Timeline Parser is the first of several independent SOC (Security Operations Center) tools, designed to integrate into a unified investigation platform over time.

---

## License

License to be determined.

---

*Timeline Parser Mark I — built for analysts who need answers fast.*