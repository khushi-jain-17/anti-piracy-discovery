import argparse
import asyncio
import datetime
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

from config import settings
from discovery import SearchOrchestrator, SearchResult
from classification import DomainClassifier
from detection import BrowserManager, PlayerDetector, NetworkSniffer
from evidence import ScreenshotCapturer, TakedownNoticeGenerator, SocialDetector
from reporting import ReportExporter, SummaryReporter

# Reconfigure stdout/stderr encoding for UTF-8 compatibility (especially on Windows terminals)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

async def run_pipeline(queries_per_lang: int = 5, max_results_per_query: int = 5, headless: bool = True):
    logger.info("=" * 65)
    logger.info("  STARTING DAZN ANTI-PIRACY DISCOVERY & VERIFICATION PIPELINE ")
    logger.info("=" * 65)

    # 1. Search Discovery
    orchestrator = SearchOrchestrator()
    discovered_items: List[SearchResult] = orchestrator.run_discovery(
        max_results_per_query=max_results_per_query,
        queries_per_lang=queries_per_lang
    )
    logger.info(f"Discovered {len(discovered_items)} unique URLs from search engines.")

    # 2. Domain Classification
    classifier = DomainClassifier()
    classified_results = [classifier.classify(item) for item in discovered_items]
    logger.info("Completed domain classification and heuristic scoring.")

    # 3. Video Player Detection & Evidence Capture via Playwright
    browser_mgr = BrowserManager(headless=headless)
    player_detector = PlayerDetector(wait_seconds=settings.PLAYER_DETECTION_WAIT_SEC)
    screenshot_capturer = ScreenshotCapturer()
    takedown_generator = TakedownNoticeGenerator()
    
    final_records: List[Dict[str, Any]] = []

    try:
        await browser_mgr.start()
        context = await browser_mgr.new_context()

        for idx, item in enumerate(classified_results, 1):
            s_res = item.search_result
            logger.info(f"[{idx}/{len(classified_results)}] Verifying {item.classification} URL: {s_res.url}")

            timestamp_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            player_detected = False
            player_type = "None"
            player_status = "No Player"
            stream_source = ""
            screenshot_path = ""
            telegram_links = []
            takedown_path = ""

            # Only open headless browser for non-allowlisted / pirate / uncertain pages or sample verification
            if item.classification in ["Pirate", "Uncertain"] or idx <= 5:
                page = await context.new_page()
                sniffer = NetworkSniffer()
                sniffer.attach_to_page(page)

                try:
                    # Navigate with timeout
                    await page.goto(s_res.url, timeout=settings.BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                    await asyncio.sleep(2)

                    # Detect player & playback status
                    detection_res = await player_detector.detect(page, sniffer)
                    player_detected = detection_res.player_detected
                    player_type = detection_res.player_type
                    player_status = detection_res.player_status
                    stream_source = detection_res.stream_source

                    # Find Telegram links (Bonus)
                    telegram_links = await SocialDetector.find_telegram_links(page)

                    # Capture screenshot evidence
                    screenshot_path = await screenshot_capturer.capture_evidence(
                        page=page,
                        url=s_res.url,
                        domain=s_res.domain,
                        timestamp_utc=timestamp_utc,
                        bounding_box=detection_res.video_bounding_box
                    )
                except Exception as e:
                    logger.warning(f"Browser navigation to {s_res.url} failed: {e}")
                    # Capture fallback screenshot record
                    screenshot_path = screenshot_capturer.generate_fallback_card(
                        filename=f"{timestamp_utc.replace(':', '-')}_{s_res.domain}_fallback.png",
                        url=s_res.url,
                        domain=s_res.domain,
                        timestamp_utc=timestamp_utc,
                        error_msg=str(e)
                    )
                finally:
                    await page.close()
            else:
                # Official allowlisted page fast-path
                player_status = "Not Applicable (Official)"
                player_type = "Official Media"

            # Create final record matching required schema
            record = {
                "search_engine": s_res.search_engine,
                "query": s_res.query,
                "rank": s_res.rank,
                "url": s_res.url,
                "domain": s_res.domain,
                "classification": item.classification,
                "confidence_score": item.confidence_score,
                "player_detected": player_detected,
                "player_type": player_type,
                "player_status": player_status,
                "stream_source": stream_source,
                "screenshot_path": screenshot_path,
                "checked_at_utc": timestamp_utc,
                "hosting_ip": item.hosting_ip,
                "asn": item.asn,
                "matched_heuristics": ", ".join(item.matched_heuristics),
                "telegram_links": ", ".join(telegram_links) if telegram_links else "None"
            }

            # Generate DMCA takedown draft for confirmed pirate sites
            if item.classification == "Pirate":
                takedown_path = takedown_generator.generate_notice(record)
                record["takedown_notice_path"] = takedown_path

            final_records.append(record)

    finally:
        await browser_mgr.stop()

    # 4. Output CSV and JSON Reports
    exporter = ReportExporter()
    csv_file = exporter.export_csv(final_records, "report.csv")
    json_file = exporter.export_json(final_records, "report.json")
    exporter.export_pirates_only(final_records, "report_pirates.csv", "report_pirates.json")

    # 5. Summary Report
    SummaryReporter.generate_summary(final_records)
    logger.info(f"Pipeline completed successfully. Outputs saved in '{settings.OUTPUT_DIR}'.")


def main():
    parser = argparse.ArgumentParser(description="DAZN Anti-Piracy Discovery & Verification CLI")
    parser.add_argument("--queries-per-lang", type=int, default=5, help="Number of queries per language category")
    parser.add_argument("--max-results", type=int, default=5, help="Max results per query search")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode (headful) instead of hidden background")
    args = parser.parse_args()

    asyncio.run(run_pipeline(
        queries_per_lang=args.queries_per_lang,
        max_results_per_query=args.max_results,
        headless=not args.visible
    ))

if __name__ == "__main__":
    main()
