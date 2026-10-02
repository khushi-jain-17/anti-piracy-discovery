import logging
from typing import List
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class SocialDetector:
    @staticmethod
    async def find_telegram_links(page: Page) -> List[str]:
        """Detect Telegram channels/groups linked on pirate streaming pages."""
        js_code = """
        () => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const tgLinks = new Set();
            for (let a of links) {
                const href = a.href || '';
                if (href.includes('t.me/') || href.includes('telegram.me/') || href.includes('telegram.dog/')) {
                    tgLinks.add(href);
                }
            }
            return Array.from(tgLinks);
        }
        """
        try:
            links = await page.evaluate(js_code)
            if isinstance(links, list) and len(links) > 0:
                logger.info(f"[SocialDetector] Discovered Telegram links: {links}")
                return links
        except Exception as e:
            logger.debug(f"Telegram link detection error: {e}")
        return []
