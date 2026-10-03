import logging
import time
import requests
from bs4 import BeautifulSoup
from typing import List
from config import settings
from .base import BaseSearchEngine, SearchResult
from .serpapi_adapter import SerpApiAdapter

logger = logging.getLogger(__name__)

class YandexSearchEngine(BaseSearchEngine):
    def __init__(self):
        super().__init__("Yandex")
        self.serpapi = SerpApiAdapter()
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        logger.info(f"[Yandex] Searching query: '{query}'")
        
        # 1. Try SerpApi if API Key provided
        if self.serpapi.api_key:
            results = self.serpapi.search_yandex(query, max_results)
            if results:
                return results

        # 2. Direct Scraper
        try:
            url = f"https://yandex.com/search/?text={requests.utils.quote(query)}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                rank = 1
                for li in soup.select("li.serp-item, div.organic"):
                    title_elem = li.select_one("h2, a.organic__url, a.link")
                    snippet_elem = li.select_one(".organic__content, .extended-text, .serp-item__text")
                    link_elem = li.select_one("a[href]")

                    if link_elem:
                        href = link_elem.get("href", "")
                        if href.startswith("http") and "yandex" not in href:
                            title = title_elem.get_text(strip=True) if title_elem else ""
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            results.append(SearchResult(
                                query=query,
                                search_engine="Yandex",
                                rank=rank,
                                url=href,
                                domain=SearchResult.extract_domain(href),
                                page_title=title,
                                snippet=snippet
                            ))
                            rank += 1
                            if rank > max_results:
                                break
                if results:
                    return results
        except Exception as e:
            logger.debug(f"[Yandex] Direct HTML scraper exception for '{query}': {e}")

        # No fabricated results: if every real source failed, report it and return nothing.
        logger.warning(
            f"[Yandex] No live results for '{query}' (SerpApi unavailable/failed and direct SERP "
            f"scrape blocked or empty). Returning 0 results - nothing is substituted."
        )
        return []
