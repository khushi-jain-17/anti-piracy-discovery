# DAZN Anti-Piracy Discovery & Verification Pipeline

An automated, end-to-end intelligence and verification pipeline designed to discover unauthorized DAZN live sports streams across regional search engines, evaluate domain legitimacy, verify active video playback in a sandboxed headless browser, and produce legally defensible DMCA takedown evidence packages.

---

## Architecture & Core Workflow

The pipeline operates across five modular stages:

1. **Search Discovery**: Executes targeted, multi-lingual search queries (English, Russian, Chinese, event-specific) across Yandex and Baidu using SerpApi with automated fallback mechanisms and URL canonicalization/deduplication.
2. **Domain Classification**: Evaluates candidate domains against an authoritative allowlist and heuristic risk scoring (brand impersonation, piracy keyword density, risky TLDs, and ad/redirect networks).
3. **Sandboxed Browser Verification**: Launches headless Chromium instances to inspect the DOM for video elements (HTML5, JW Player, Video.js, Clappr), resolve embedded iframes, and intercept network traffic for active streaming manifests (`.m3u8` HLS, `.mpd` DASH).
4. **Evidence Collection & Intelligence**:
   - Captures timestamped full-page and cropped video player screenshots.
   - Extracts network hosting metadata (IP address and ASN/ISP resolution).
   - Discovers affiliated piracy distribution channels (e.g., Telegram links).
   - Performs perceptual hash matching (`dHash` and `aHash`) against DAZN reference logos to detect unauthorized on-screen brand assets.
5. **Reporting & Legal Notice Generation**: Produces audit-ready CSV/JSON datasets, an executive summary dashboard, and auto-populated DMCA takedown notice drafts for confirmed pirate domains.

---

## Project Structure

```text
anti-piracy-discovery/
├── assets/                  # Brand reference assets (official DAZN logos for visual matching)
├── classification/          # Domain classification logic, heuristic scorer, and DNS/ASN lookup
├── config/                  # Global settings, heuristics weights, and official domain allowlist
├── detection/               # Playwright browser manager, player inspector, and network sniffer
├── discovery/               # Search engine adapters (Yandex, Baidu) and search orchestrator
├── evidence/                # Screenshot capture, DMCA notice generator, logo matcher, social link detector
├── outputs/                 # Generated audit reports, screenshots, and takedown notices
├── reporting/               # CSV, JSON, and Markdown summary export handlers
├── scripts/                 # Utility scripts (e.g., reference logo fetcher)
├── tasks/                   # Celery distributed tasks (asynchronous verification worker)
├── tests/                   # Pytest test suite covering core modules (including Celery & Redis)
├── celery_app.py            # Celery application configuration and Redis broker bindings
├── docker-compose.yml       # Production multi-service stack (Redis broker, Celery worker cluster, pipeline)
├── Dockerfile               # Container build definition for pipeline execution
├── main.py                  # CLI entrypoint for discovery & verification pipeline (standalone & distributed)
└── requirements.txt         # Project Python dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- [Optional] Docker and Docker Compose

### 1. Installation

Clone the repository and set up a virtual environment:

```bash
# Clone repository
git clone <repository-url>
cd anti-piracy-discovery

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 2. Configuration

Create a `.env` file in the project root:

```env
SERPAPI_API_KEY=your_serpapi_key_here
MAX_RESULTS_PER_QUERY=10
HEADLESS=true
BROWSER_TIMEOUT_MS=30000
PLAYER_DETECTION_WAIT_SEC=5
CONCURRENCY=3
LOG_LEVEL=INFO
```

#### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `SERPAPI_API_KEY` | `""` | SerpApi key for live Yandex / Baidu search queries (optional fallback used if omitted) |
| `MAX_RESULTS_PER_QUERY` | `10` | Maximum search results to ingest per query |
| `HEADLESS` | `true` | Run Playwright Chromium in headless mode |
| `BROWSER_TIMEOUT_MS` | `30000` | Browser navigation timeout in milliseconds |
| `PLAYER_DETECTION_WAIT_SEC` | `5` | Video player evaluation window in seconds |
| `CONCURRENCY` | `3` | Concurrent worker limit for browser verification |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL for caching and message broker |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery message broker endpoint |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery task result backend endpoint |
| `REDIS_CACHE_TTL_SEC` | `86400` | 24-hour domain classification cache TTL |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Usage

### 1. Standalone Execution Mode (Local Async Playwright)

Execute the discovery and verification process via `main.py` directly (includes automatic Redis caching if a Redis instance is available, with graceful in-memory fallback):

```bash
# Standard run with default parameters
python main.py

# Run directly on machine
python main.py --queries-per-lang 5 --max-results 5

# Debug mode with visible (headful) browser window
python main.py --queries-per-lang 2 --max-results 3 --visible
```

### 2. Production Distributed Mode (Celery + Redis Worker Pool)

Scale the pipeline horizontally to handle high throughput across a distributed worker pool:

```bash
# Terminal 1: Start Redis (or use Docker container)
redis-server

# Terminal 2: Start Celery verification worker pool
celery -A celery_app worker --loglevel=INFO -c 3

# Terminal 3: Dispatch discovery batch into Celery queue
python main.py --distributed --queries-per-lang 5 --max-results 5
```

#### CLI Arguments

- `--queries-per-lang` *(int, default: 5)*: Number of targeted search queries to run per language/region category.
- `--max-results` *(int, default: 5)*: Maximum search results retrieved per query.
- `--visible` *(flag)*: Runs the browser in headful mode for real-time visual inspection.
- `--distributed` *(flag)*: Dispatches verification tasks to the Celery worker cluster and coordinates via Redis broker.

### Run Tests

Execute the automated test suite with `pytest`:

```bash
python -m pytest -v
```

---

## Docker Deployment (Full Production Stack)

```bash
# 1. Build the Docker image
docker build -t dazn-anti-piracy .

# 2. Run the discovery pipeline
docker compose up discovery-pipeline

# 3. Run the test suite inside Docker
docker compose run --rm test

```

To build and run the multi-container stack (Redis broker, Celery worker cluster, and discovery orchestrator) inside isolated containerized sandboxes:

```bash
# 1. Build and start Redis broker + Celery worker cluster in the background
docker compose up -d redis celery-worker

# 2. Run the distributed discovery and verification pipeline
docker compose up discovery-pipeline

# 3. Run the complete automated test suite inside Docker
docker compose run --rm test

# Rebuild the container and run the discovery pipeline
docker compose up --build piracy-pipeline
```

# Run the Full Distributed Stack with Celery & Redis
```bash
# 1. Start Redis and Celery worker in the background
docker compose up -d --build redis celery-worker

# 2. Run the distributed pipeline
docker compose up --build discovery-pipeline-distributed

```

Pipeline artifacts and reports are mounted to `./outputs` on the host machine.

---

## Output Deliverables (`outputs/`)

Each execution populates the `outputs/` directory with structured intelligence and evidence:

| Artifact | Format | Description |
| :--- | :--- | :--- |
| `report.csv` / `report.json` | CSV / JSON | Complete dataset containing every discovered URL, classification score, player status, and metadata. |
| `report_pirates.csv` / `report_pirates.json` | CSV / JSON | Filtered dataset isolating confirmed and high-probability pirate live streams. |
| `summary.md` | Markdown | Executive dashboard summarizing total scanned URLs, domain classifications, and active playback statistics. |
| `screenshots/` | PNG | Timestamped full-page screenshots and cropped video player regions (`YYYY-MM-DD_HH-MM-SS_domain.png`). |
| `takedown_notices/` | Markdown | Legally formatted DMCA takedown notice drafts populated with URL, host ASN, IP, and timestamp. |

