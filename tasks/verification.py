import asyncio
import datetime
import logging
from typing import Dict, Any
from celery_app import app
from config import settings
from classification.cache import RedisDomainCache
from detection import BrowserManager, PlayerDetector, NetworkSniffer
from evidence import ScreenshotCapturer, TakedownNoticeGenerator, SocialDetector, LogoMatcher, LogoMatchResult

logger = logging.getLogger("celery_tasks")

async def _verify_url_async(item: Dict[str, Any]) -> Dict[str, Any]:
    """Execute asynchronous Playwright verification, sniffing, and evidence capture."""
    url = item.get("url", "")
    domain = item.get("domain", "")
    classification = item.get("classification", "Uncertain")
    timestamp_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    browser_mgr = BrowserManager(headless=settings.HEADLESS)
    player_detector = PlayerDetector(wait_seconds=settings.PLAYER_DETECTION_WAIT_SEC)
    screenshot_capturer = ScreenshotCapturer()
    takedown_generator = TakedownNoticeGenerator()
    logo_matcher = LogoMatcher()

    player_detected = False
    player_type = "None"
    player_status = "No Player"
    stream_source = ""
    screenshot_path = ""
    telegram_links = []
    takedown_path = ""

    await browser_mgr.start()
    try:
        context = await browser_mgr.new_context()
        page = await context.new_page()
        sniffer = NetworkSniffer()
        sniffer.attach_to_page(page)

        try:
            await page.goto(url, timeout=settings.BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Detect player & playback status
            detection_res = await player_detector.detect(page, sniffer)
            player_detected = detection_res.player_detected
            player_type = detection_res.player_type
            player_status = detection_res.player_status
            stream_source = detection_res.stream_source

            # Find Telegram channels
            telegram_links = await SocialDetector.find_telegram_links(page)

            # Capture evidence screenshots
            screenshot_path = await screenshot_capturer.capture_evidence(
                page=page,
                url=url,
                domain=domain,
                timestamp_utc=timestamp_utc,
                bounding_box=detection_res.video_bounding_box
            )
        except Exception as e:
            logger.warning(f"[CeleryWorker] Navigation error for {url}: {e}")
            screenshot_path = screenshot_capturer.generate_fallback_card(
                filename=f"{timestamp_utc.replace(':', '-')}_{domain}_fallback.png",
                url=url,
                domain=domain,
                timestamp_utc=timestamp_utc,
                error_msg=str(e)
            )
        finally:
            await page.close()
    finally:
        await browser_mgr.stop()

    # Perceptual logo matching
    logo_result = LogoMatchResult()
    if screenshot_path and not screenshot_path.endswith("fallback.png"):
        evidence_images = [screenshot_path]
        ts_slug = timestamp_utc.replace(":", "-").replace(" ", "_")
        player_crop = settings.SCREENSHOT_DIR / f"{ts_slug}_{domain.replace('.', '_').replace('/', '_')}_player.png"
        if player_crop.exists():
            evidence_images.append(str(player_crop))
        logo_result = logo_matcher.match_images(evidence_images)

    record = {
        "search_engine": item.get("search_engine", "Unknown"),
        "query": item.get("query", ""),
        "rank": item.get("rank", 0),
        "url": url,
        "domain": domain,
        "classification": classification,
        "confidence_score": item.get("confidence_score", 0),
        "player_detected": player_detected,
        "player_type": player_type,
        "player_status": player_status,
        "stream_source": stream_source,
        "screenshot_path": screenshot_path,
        "checked_at_utc": timestamp_utc,
        "hosting_ip": item.get("hosting_ip", "Unknown"),
        "asn": item.get("asn", "Unknown"),
        "matched_heuristics": item.get("matched_heuristics", ""),
        "telegram_links": ", ".join(telegram_links) if telegram_links else "None",
        "logo_match": logo_result.matched,
        "logo_match_details": logo_result.summary,
        "logo_match_similarity": logo_result.best_similarity,
    }

    if classification == "Pirate":
        takedown_path = takedown_generator.generate_notice(record)
        record["takedown_notice_path"] = takedown_path

    return record


@app.task(name="tasks.verify_url_task", bind=True, max_retries=2, default_retry_delay=5)
def verify_url_task(self, item_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery task that executes URL verification across worker pool.
    Utilizes Redis caching for 24-hour domain deduplication.
    """
    domain = item_dict.get("domain", "")
    url = item_dict.get("url", "")
    classification = item_dict.get("classification", "Uncertain")
    logger.info(f"[CeleryTask] Processing task {self.request.id} for domain '{domain}' ({classification})")

    cache = RedisDomainCache()

    # 1. Check Redis cache first (Deduplication Layer)
    cached_record = cache.get(domain)
    if cached_record:
        logger.info(f"[CeleryTask] Redis Cache HIT for domain '{domain}' - skipping browser run")
        # Update search context for current query
        cached_copy = dict(cached_record)
        cached_copy["search_engine"] = item_dict.get("search_engine", cached_copy.get("search_engine", ""))
        cached_copy["query"] = item_dict.get("query", cached_copy.get("query", ""))
        cached_copy["rank"] = item_dict.get("rank", cached_copy.get("rank", 0))
        return cached_copy

    # 2. Official allowlisted fast-path
    if classification == "Official":
        timestamp_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "search_engine": item_dict.get("search_engine", ""),
            "query": item_dict.get("query", ""),
            "rank": item_dict.get("rank", 0),
            "url": url,
            "domain": domain,
            "classification": "Official",
            "confidence_score": item_dict.get("confidence_score", 95),
            "player_detected": False,
            "player_type": "Official Media",
            "player_status": "Not Applicable (Official)",
            "stream_source": "",
            "screenshot_path": "",
            "checked_at_utc": timestamp_utc,
            "hosting_ip": item_dict.get("hosting_ip", "Unknown"),
            "asn": item_dict.get("asn", "Unknown"),
            "matched_heuristics": item_dict.get("matched_heuristics", "ALLOWLIST_MATCH"),
            "telegram_links": "None",
            "logo_match": False,
            "logo_match_details": "No match",
            "logo_match_similarity": 0.0,
        }
        cache.set(domain, record)
        return record

    # 3. Execute browser verification
    try:
        final_record = asyncio.run(_verify_url_async(item_dict))
        # Store in Redis cache for subsequent searches
        cache.set(domain, final_record)
        return final_record
    except Exception as exc:
        logger.error(f"[CeleryTask] Failure verifying {url}: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # Fallback error record
            timestamp_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            return {
                "search_engine": item_dict.get("search_engine", ""),
                "query": item_dict.get("query", ""),
                "rank": item_dict.get("rank", 0),
                "url": url,
                "domain": domain,
                "classification": classification,
                "confidence_score": item_dict.get("confidence_score", 0),
                "player_detected": False,
                "player_type": "None",
                "player_status": "Error / Unreachable",
                "stream_source": "",
                "screenshot_path": "",
                "checked_at_utc": timestamp_utc,
                "hosting_ip": item_dict.get("hosting_ip", "Unknown"),
                "asn": item_dict.get("asn", "Unknown"),
                "matched_heuristics": item_dict.get("matched_heuristics", ""),
                "telegram_links": "None",
                "logo_match": False,
                "logo_match_details": "No match",
                "logo_match_similarity": 0.0,
            }
