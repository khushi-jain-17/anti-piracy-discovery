# DAZN Anti-Piracy Discovery & Verification Pipeline

An automated, end-to-end anti-piracy discovery and evidence collection pipeline designed to find, classify, verify, and generate legally enforceable DMCA takedown evidence against illegal DAZN live streams.

---

## ðŸš€ Quick Start

### 1. Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Run Main Discovery & Verification Pipeline
```bash

python main.py --queries-per-lang 5 --max-results 5
python main.py --queries-per-lang 2 --max-results 3

```

### Docker commands to run application
docker build -t dazn-anti-piracy .     
docker compose up discovery-pipeline                                                         
docker compose run --rm test  

docker compose build --no-cache

---

## ðŸ“ Output Artifacts (`outputs/`)

- `report.csv`: Complete discovery & classification dataset.
- `report.json`: JSON output matching mandatory schema.
- `report_pirates.csv` / `report_pirates.json`: Pirate-only output dataset (excluding allowlisted domains).
- `summary.md`: Summary report dashboard.
- `screenshots/`: Timestamped full-page and cropped player screenshots (`YYYY-MM-DD_HH-MM-SS_domain_hash.png`).
- `takedown_notices/`: Auto-generated DMCA takedown notice markdown drafts.

---

## âš™ï¸ Configuration (`.env`)

Environment variables are managed in `.env` (excluded from git via `.gitignore`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `SERPAPI_API_KEY` | SerpApi key for live Yandex / Baidu search queries |
| `MAX_RESULTS_PER_QUERY` | `10` | Max search results to process per query |
| `HEADLESS` | `true` | Run Playwright Chromium in headless mode |
| `BROWSER_TIMEOUT_MS` | `30000` | Page navigation timeout (ms) |
| `PLAYER_DETECTION_WAIT_SEC` | `5` | Inspection window wait time for video playback |
| `CONCURRENCY` | `3` | Parallel page verification concurrency |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## âš ï¸ Known Limitations

1. **Search Engine Anti-Bot Controls:** Search engines (Yandex, Baidu) periodically enforce CAPTCHAs or rate-limiting on direct SERP HTML scraping. The pipeline handles this gracefully via SerpApi or heuristic SERP fallbacks.
2. **Geo-blocking & Regional Access:** Certain regional streams (e.g. Russia, China) restrict access based on client IP location. Rotating proxy support (BrightData/Oxylabs) is recommended for production scaling.
3. **JS Obfuscation & Dynamic Token Expiry:** Advanced pirate sites employ obfuscated stream URLs (`.m3u8` with short-lived tokens). The Network Sniffer captures outgoing requests directly from page context during rendering.


---

## Logo / On-screen Graphic Matching (Perceptual Hashing)

Evidence screenshots are scanned against reference DAZN logos in `assets/reference_logos/` (dHash + aHash, multi-scale sliding window - see `evidence/logo_matcher.py`). Results appear as `logo_match`, `logo_match_details` and `logo_match_similarity` in the reports and in the DMCA drafts. The bundled logos are synthetic placeholders (`python scripts/generate_reference_logos.py`); replace them with real licensed DAZN assets. Tune with `LOGO_DHASH_THRESHOLD` / `LOGO_AHASH_THRESHOLD` in `.env`.
