import os
import datetime
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import Page
from config import settings

logger = logging.getLogger(__name__)

class ScreenshotCapturer:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or settings.SCREENSHOT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def capture_evidence(
        self,
        page: Page,
        url: str,
        domain: str,
        timestamp_utc: str,
        bounding_box: Optional[Dict[str, float]] = None
    ) -> str:
        """Capture full-page screenshot and save to disk with UTC timestamp filename."""
        safe_domain = domain.replace(".", "_").replace("/", "_")
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        ts_slug = timestamp_utc.replace(":", "-").replace(" ", "_")
        
        filename = f"{ts_slug}_{safe_domain}_{url_hash}.png"
        filepath = self.output_dir / filename

        try:
            # Capture full page screenshot
            await page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"[Screenshot] Captured full page evidence: {filename}")

            # If player bounding box is available, crop and save player screenshot
            if bounding_box and bounding_box.get("width", 0) > 50 and bounding_box.get("height", 0) > 50:
                self._crop_player_area(filepath, bounding_box, f"{ts_slug}_{safe_domain}_player.png")

            try:
                return str(filepath.relative_to(settings.BASE_DIR))
            except ValueError:
                return str(filepath)

        except Exception as e:
            logger.error(f"[Screenshot] Failed to capture screenshot for {url}: {e}")
            return self.generate_fallback_card(filename, url, domain, timestamp_utc, str(e))

    def _crop_player_area(self, full_image_path: Path, bbox: Dict[str, float], crop_filename: str):
        try:
            with Image.open(full_image_path) as img:
                left = max(0, int(bbox.get("x", 0)))
                top = max(0, int(bbox.get("y", 0)))
                right = min(img.width, left + int(bbox.get("width", 300)))
                bottom = min(img.height, top + int(bbox.get("height", 200)))
                
                if right > left and bottom > top:
                    cropped = img.crop((left, top, right, bottom))
                    cropped_path = self.output_dir / crop_filename
                    cropped.save(cropped_path)
                    logger.info(f"[Screenshot] Cropped player area evidence: {crop_filename}")
        except Exception as e:
            logger.debug(f"Player crop failed: {e}")

    def generate_fallback_card(
        self,
        filename: str,
        url: str = "N/A",
        domain: str = "N/A",
        timestamp_utc: str = "N/A",
        error_msg: str = "Domain Offline or Unreachable"
    ) -> str:
        """Generate a clean, high-contrast Evidence Card image when web page navigation fails."""
        filepath = self.output_dir / filename
        
        # Create a clean light card (1280x720)
        img = Image.new('RGB', (1280, 720), color=(240, 243, 246))
        draw = ImageDraw.Draw(img)

        # Draw red header bar
        draw.rectangle([(0, 0), (1280, 100)], fill=(180, 30, 30))
        draw.text((40, 32), "DAZN CONTENT PROTECTION - DOMAIN EVIDENCE CARD", fill=(255, 255, 255))

        # Draw white content box
        draw.rectangle([(40, 130), (1240, 660)], fill=(255, 255, 255), outline=(210, 215, 220), width=2)

        # Content text lines
        draw.text((70, 160), "STATUS: OFFLINE / UNREACHABLE PIRATE DOMAIN", fill=(180, 30, 30))
        draw.text((70, 220), f"TARGET DOMAIN : {domain}", fill=(20, 20, 20))
        draw.text((70, 270), f"TARGET URL    : {url}", fill=(20, 20, 20))
        draw.text((70, 320), f"CHECKED UTC   : {timestamp_utc}", fill=(20, 20, 20))
        draw.text((70, 370), f"ERROR / REASON: {error_msg[:90]}", fill=(100, 100, 100))

        # Divider
        draw.line([(70, 430), (1210, 430)], fill=(230, 230, 230), width=2)

        # Footer note
        draw.text((70, 460), "LEGAL EVIDENCE NOTE:", fill=(40, 40, 40))
        draw.text((70, 500), "This domain was identified during automated piracy discovery but failed live browser render", fill=(80, 80, 80))
        draw.text((70, 530), "(likely due to DNS revocation, host shutdown, or anti-bot network filtering).", fill=(80, 80, 80))

        img.save(filepath)
        logger.info(f"[Screenshot] Generated clean evidence card: {filename}")
        try:
            return str(filepath.relative_to(settings.BASE_DIR))
        except ValueError:
            return str(filepath)


    def _generate_fallback_image(self, filename: str) -> str:
        return self.generate_fallback_card(filename)
