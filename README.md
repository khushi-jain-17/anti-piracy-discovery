# DAZN Anti-Piracy Discovery & Verification Pipeline

An automated, end-to-end anti-piracy discovery and evidence collection pipeline designed to find, classify, verify, and generate legally enforceable DMCA takedown evidence against illegal DAZN live streams.

---

## 🚀 Quick Start

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
```

### Docker commands to run application
docker build -t dazn-anti-piracy .     
docker compose up discovery-pipeline                                                         
docker compose run --rm test  

---

## 📊 Module 5: Pipeline Execution Summary Report

| Metric | Count |
| :--- | :---: |
| **Total URLs Discovered** | 20 |
| **Official / Authorised Domains** | 3 |
| **Suspected Pirate Domains** | 12 |
| **Uncertain Domains** | 5 |
| **Video Players Detected** | 10 |
| **Actively Playing Streams** | 7 |

### Top Confirmed Pirate Domains
| Domain | Frequency |
| :--- | :--- |
| `dazn-live.xyz` | 4 |
| `westreamf1.st` | 3 |
| `f1hd.net` | 2 |
| `motogplive.com` | 2 |
| `vipleague.st` | 1 |

---

## 📁 Output Artifacts (`outputs/`)

- `report.csv`: Complete discovery & classification dataset.
- `report.json`: JSON output matching mandatory schema.
- `report_pirates.csv` / `report_pirates.json`: Pirate-only output dataset (excluding allowlisted domains).
- `summary.md`: Summary report dashboard.
- `screenshots/`: Timestamped full-page and cropped player screenshots (`YYYY-MM-DD_HH-MM-SS_domain_hash.png`).
- `takedown_notices/`: Auto-generated DMCA takedown notice markdown drafts.

---

## 🛡️ Architecture & Modules

1. **Module 1: Search Discovery (`discovery/`)** - Multi-language Yandex & Baidu SERP discovery with canonical URL deduplication.
2. **Module 2: Domain Classification (`classification/`)** - Allowlist matching & 0–100 heuristic scoring (Brand impersonation, keywords including HD, WHOIS privacy, ad networks).
3. **Module 3: Video Player Detection (`detection/`)** - Playwright headless sandbox inspecting HTML5 `<video>`, JS players (JW Player, Video.js, Clappr, hls.js, etc.), iframe embeds, and `.m3u8` / `.mpd` network sniffer.
4. **Module 4: Evidence Capture (`evidence/`)** - Full-page & cropped player screenshots with UTC timestamping, stream source extraction, and fallback card generation.
5. **Module 5: Output & Reporting (`reporting/`)** - Export to CSV/JSON matching all mandatory fields plus hosting IP/ASN intelligence and summary dashboard.
