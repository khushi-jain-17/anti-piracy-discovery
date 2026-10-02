## 1. System Architecture Overview

The Anti-Piracy Discovery & Verification System is designed as a modular, end-to-end automated pipeline to discover illegal live streams across regional search engines (Yandex & Baidu), classify domain legitimacy, verify active video playback in a sandboxed headless browser, and produce legally enforceable evidence packages for takedown notices.

### System Flow Diagram

```mermaid
flowchart TD
    subgraph STAGE1 ["Stage 1: Multi-Engine Search Discovery"]
        Q["Multi-Language Search Queries<br>(English, Russian, Chinese, Event-Based)"] --> ORCH["Search Orchestrator"]
        ORCH --> YANDEX["Yandex Engine Adapter<br>(SerpApi / HTML SERP)"]
        ORCH --> BAIDU["Baidu Engine Adapter<br>(SerpApi / HTML SERP)"]
        YANDEX --> DUP["Deduplication & Canonical URL Normalizer"]
        BAIDU --> DUP
    end

    subgraph STAGE2 ["Stage 2: Domain Classification Engine"]
        DUP --> CLASSIFY["Domain Classifier & Heuristic Scorer"]
        CLASSIFY --> CHECK{"Is Domain<br>Allowlisted?"}
        
        CHECK -->|"YES (dazn.com, YouTube, News)"| OFF["OFFICIAL DOMAIN<br>Confidence: 95% | Fast-Track"]
        CHECK -->|"NO"| HEURISTIC["Evaluate Heuristic Signals:<br>• Brand Impersonation (+50)<br>• Piracy Keywords in Domain/URL/Title/Body (+15..35)<br>• High-Risk TLDs .xyz, .top (+20)<br>• Ad & Popup Networks (+25)<br>• Anonymous WHOIS Privacy (+15)"]
        HEURISTIC --> SCORE["Compute Confidence Score (0 - 100)"]
        SCORE --> EVAL{"Confidence<br>Threshold"}
        EVAL -->|"Score >= 40"| PIRATE["SUSPECTED PIRATE<br>Trigger Headless Sandbox"]
        EVAL -->|"20 <= Score < 40"| UNCERTAIN["UNCERTAIN DOMAIN<br>Trigger Headless Sandbox"]
        EVAL -->|"Score < 20"| OFF
    end

    subgraph STAGE3 ["Stage 3: Sandboxed Playwright Verification"]
        PIRATE --> PLAYWRIGHT["Playwright Headless Chromium Sandbox<br>(Ad & Popup Blocked Context)"]
        UNCERTAIN --> PLAYWRIGHT
        
        PLAYWRIGHT --> DOM_INSPECT["DOM Video Inspector<br>(HTML5, JW Player, Video.js, Clappr, hls.js)"]
        PLAYWRIGHT --> IFRAME_INSPECT["iframe Embed Inspector<br>(Extracts Embed Sources & Host Domains)"]
        PLAYWRIGHT --> NET_SNIFF["Network Stream Sniffer<br>(Intercepts .m3u8 HLS / .mpd DASH Manifests & Chunks)"]
        
        DOM_INSPECT --> PLAYBACK_EVAL["Playback Status Evaluator<br>(currentTime Advancement / Segment Requests)"]
        IFRAME_INSPECT --> PLAYBACK_EVAL
        NET_SNIFF --> PLAYBACK_EVAL
    end

    subgraph STAGE4 ["Stage 4: Network Intelligence & Evidence Capture"]
        PLAYBACK_EVAL --> WHOIS_LOOKUP["IP & RDAP / ASN Lookup<br>(Identifies Cloudflare, Fastly, Bulletproof Host)"]
        PLAYBACK_EVAL --> SCREENSHOT["Timestamped Screenshot Capturer<br>(Full Page & Cropped Player Area)"]
        PLAYBACK_EVAL --> TAKEDOWN["Auto DMCA Takedown Notice Generator"]
        PLAYBACK_EVAL --> TELEGRAM["Social & Telegram Link Scraper"]
    end

    subgraph STAGE5 ["Stage 5: Reporting & Deliverables"]
        OFF --> EXPORTER["Report Exporter & Summary Engine"]
        WHOIS_LOOKUP --> EXPORTER
        SCREENSHOT --> EXPORTER
        TAKEDOWN --> EXPORTER
        TELEGRAM --> EXPORTER
        
        EXPORTER --> CSV_OUT["CSV Datasets<br>(report.csv & report_pirates.csv)"]
        EXPORTER --> JSON_OUT["JSON Datasets<br>(report.json & report_pirates.json)"]
        EXPORTER --> DASHBOARD["Executive Summary Dashboard<br>(summary.md & Console Summary)"]
    end

    classDef official fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724;
    classDef pirate fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#721c24;
    classDef uncertain fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#856404;
    classDef decision fill:#d1ecf1,stroke:#17a2b8,stroke-width:2px,color:#0c5460;

    class OFF official;
    class PIRATE pirate;
    class UNCERTAIN uncertain;
    class CHECK,EVAL decision;
```

---

## 2. Key Modules & Design Decisions

### Module 1: Search Discovery (`discovery/`)
- **Multi-Engine Support:** Integrates Yandex (Russia/CIS focus) and Baidu (China focus).
- **Adaptability:** Operates via SerpApi (when `SERPAPI_API_KEY` is present), direct SERP HTML scraping, or built-in fallback parser to handle search engine anti-bot challenges gracefully.
- **Deduplication:** Aggregates multi-language query results and deduplicates by canonical URL structure and domain name to prevent redundant verification.

### Module 2: Domain Classification (`classification/`)
- **Allowlist Filtering:** Checks candidate domains against an extensible allowlist (`dazn.com`, `kayosports.com.au`, `foxtel.com.au`, `binge.com.au`, official social accounts, app stores, Wikipedia, and verified media news sites).
- **Heuristic Scoring Model (0-100):** Evaluates non-allowlisted domains based on:
  - Brand Impersonation (e.g., `dazn-live.xyz`, `watchdazn.com`): **+50 pts**
  - High-Risk TLDs (`.xyz`, `.top`, `.stream`, `.cc`, `.ru`, `.cn`): **+20 pts**
  - Piracy Keywords in Domain / URL / Title / Snippet (`free`, `stream`, `iptv`, `zhibo`, `m3u8`): **+15 to +35 pts**
- **Classification Thresholds:**
  - `Confidence >= 40`: **Pirate**
  - `Confidence 20-39`: **Uncertain**
  - `Confidence < 20`: **Official**
- **Network Intelligence (Bonus):** Performs IP resolution and RDAP/ASN lookup (e.g. Cloudflare, Fastly, bulletproof host identification) for takedown routing.

### Module 3 & 4: Playwright Video Player Detection & Evidence (`detection/`, `evidence/`)
- **Sandboxed Execution:** Headless Chromium instance blocks known pop-up / ad networks for security and speed.
- **Player Types Detected:** HTML5 `<video>`, iframe embeds (`vidsrc`, `streamtape`, etc.), and JS player libraries (`JW Player`, `Video.js`, `Clappr`, `hls.js`, `Flowplayer`, `Plyr`).
- **Network Stream Sniffing:** Intercepts outgoing request traffic to detect `.m3u8` (HLS) and `.mpd` (DASH) live streaming manifests during page render.
- **Playback Validation:** Measures `currentTime` advancement over time or presence of active streaming manifest segments to distinguish between `Player Present - Not Playing` vs `Player Present - Playing`.
- **Evidence Capture:** Takes full-page and cropped player screenshots with UTC timestamping, extracts primary stream URLs, generates DMCA notices, and identifies associated Telegram link channels.

---

## 3. High-Throughput Scaling Architecture (1,000+ URLs in 2 Hours)

To scale from prototype to production handling **1,000+ URLs in 2 hours (~8-9 URLs/sec)**, the system would be architected as follows:

```
[SERP Discovery Cron / API] ──> [Redis Queue / RabbitMQ] ──> [Celery / Worker Pool (10-20 Nodes)]
                                                                    │
                                                     ┌──────────────┴──────────────┐
                                                     ▼                             ▼
                                          [Async Playwright Cluster]      [PostgreSQL / S3 Evidence]
```

### Key Scaling Strategies:
1. **Containerized Sandbox Deployment (Docker / Kubernetes):**
   - The pipeline runs inside an isolated Docker container based on `mcr.microsoft.com/playwright/python`.
   - Protects production infrastructure against malicious web scripts, exploit payloads, and drive-by downloads on unknown pirate streaming sites.
   - Mounted volume volumes (`/app/outputs`) persist output CSV/JSON reports, timestamped screenshot evidence, and auto-generated DMCA takedown notice drafts back to host storage or S3 buckets.

2. **Concurrency & Worker Pools:**
   - Use `asyncio` with Playwright `BrowserContext` pooling (reusing browser instances across requests rather than launching a new browser process per URL).
   - Horizontal scaling via Docker container worker nodes managed by Kubernetes (K8s) or AWS ECS.

3. **Distributed Job Queueing:**
   - Decouple Discovery from Verification using **Celery + Redis** or AWS SQS.
   - Priority queues: Fast-path allowlist domains vs heavy Playwright player checks.

4. **Caching & Deduplication:**
   - **Redis Cache Layer:** Cache domain classification results (TTL: 24 hours). Known official or defunct domains do not re-trigger headless browser checks.

5. **Proxy & Geo-Location Strategy:**
   - Residential and datacenter proxy rotation (e.g., BrightData / Oxylabs) to bypass geo-restrictions for regional streams (Russia, China, EU).

6. **Storage & Evidence Management:**
   - Evidence screenshots stored directly in AWS S3 or Google Cloud Storage with presigned URLs.
   - Structured results stored in PostgreSQL with Elasticsearch for rapid domain querying and historical threat tracking.

---

## 4. Key Assumptions & Constraints

- Search engines may enforce CAPTCHAs or rate limits; the module falls back to fallback SERP parsers or SerpApi to guarantee execution reliability.
- Live stream detection relies on DOM state and network traffic within a 5-10 second inspection window per page.
- All browsing is strictly sandboxed inside Docker container instances without downloading executables or triggering third-party popups.
