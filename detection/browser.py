import logging
from typing import AsyncGenerator
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import settings

logger = logging.getLogger(__name__)

# Ad and tracking domains to block for safety compliance
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}  # Allows initial scripts/iframes while blocking dangerous media downloads if needed
BLOCKED_DOMAINS = [
    "doubleclick.net", "adservice.google.com", "popads.net", "popcash.net",
    "exoclick.com", "juicyads.com", "bet365.com", "1xbet.com", "adsterra.com"
]

class BrowserManager:
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else settings.HEADLESS
        self._playwright = None
        self._browser: Browser = None

    async def start(self):
        if not self._playwright:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-popup-blocking=false",  # Keep popup blocking enabled
                ]
            )
            logger.info("Playwright Chromium browser started successfully.")

    async def stop(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.info("Playwright Chromium browser stopped.")

    async def new_context(self) -> BrowserContext:
        if not self._browser:
            await self.start()
        
        context = await self._browser.new_context(
            user_agent=settings.USER_AGENT,
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )

        # Abort ad network and malicious popup requests (Safety & Ethical constraint)
        async def route_handler(route, request):
            url = request.url.lower()
            if any(ad_domain in url for ad_domain in BLOCKED_DOMAINS):
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", route_handler)
        return context
