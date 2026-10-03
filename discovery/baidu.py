import logging
import requests
from bs4 import BeautifulSoup
from typing import List
from config import settings
from .base import BaseSearchEngine, SearchResult
from .serpapi_adapter import SerpApiAdapter

logger = logging.getLogger(__name__)

class BaiduSearchEngine(BaseSearchEngine):
    def __init__(self):
        super().__init__("Baidu")
        self.serpapi = SerpApiAdapter()
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        logger.info(f"[Baidu] Searching query: '{query}'")

        # 1. Try SerpApi if API Key provided
        if self.serpapi.api_key:
            results = self.serpapi.search_baidu(query, max_results)
            if results:
                return results

        # 2. Direct Scraper
        try:
            url = f"https://www.baidu.com/s?wd={requests.utils.quote(query)}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                rank = 1
                for div in soup.select("div.c-container, div.result"):
                    title_elem = div.select_one("h3, a")
                    snippet_elem = div.select_one(".c-abstract, .c-span-last")
                    link_elem = div.select_one("a[href]")

                    if link_elem:
                        href = link_elem.get("href", "")
                        if href.startswith("http"):
                            title = title_elem.get_text(strip=True) if title_elem else ""
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            results.append(SearchResult(
                                query=query,
                                search_engine="Baidu",
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
            logger.debug(f"[Baidu] Direct HTML scraper exception for '{query}': {e}")

        # No fabricated results: if every real source failed, report it and return nothing.
        logger.warning(
            f"[Baidu] No live results for '{query}' (SerpApi unavailable/failed and direct SERP "
            f"scrape blocked or empty). Returning 0 results - nothing is substituted."
        )
        return []
