import logging
from typing import List
import requests
from config import settings
from .base import SearchResult
import os

logger = logging.getLogger(__name__)

class SerpApiAdapter:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.SERPAPI_API_KEY
        # self.api_key = os.getenv("SERPAPI_API_KEY", self.api_key)
        self.base_url = "https://serpapi.com/search.json"

    def search_yandex(self, query: str, max_results: int = 10) -> List[SearchResult]:
        if not self.api_key:
            return []
        
        params = {
            "engine": "yandex",
            "text": query,
            "api_key": self.api_key,
            "num": max_results
        }
        try:
            resp = requests.get(self.base_url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"SerpApi Yandex error status {resp.status_code}: {resp.text[:100]}")
                return []
            
            data = resp.json()
            organic = data.get("organic_results", [])
            results = []
            for rank, item in enumerate(organic[:max_results], 1):
                link = item.get("link", "")
                if not link:
                    continue
                results.append(SearchResult(
                    query=query,
                    search_engine="Yandex",
                    rank=rank,
                    url=link,
                    domain=SearchResult.extract_domain(link),
                    page_title=item.get("title", ""),
                    snippet=item.get("snippet", "")
                ))
            return results
        except Exception as e:
            logger.error(f"SerpApi Yandex search failed for '{query}': {e}")
            return []

    def search_baidu(self, query: str, max_results: int = 10) -> List[SearchResult]:
        if not self.api_key:
            return []
        
        params = {
            "engine": "baidu",
            "q": query,
            "api_key": self.api_key,
            "rn": max_results
        }
        try:
            resp = requests.get(self.base_url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"SerpApi Baidu error status {resp.status_code}: {resp.text[:100]}")
                return []
            
            data = resp.json()
            organic = data.get("organic_results", [])
            results = []
            for rank, item in enumerate(organic[:max_results], 1):
                link = item.get("link", "")
                if not link:
                    continue
                results.append(SearchResult(
                    query=query,
                    search_engine="Baidu",
                    rank=rank,
                    url=link,
                    domain=SearchResult.extract_domain(link),
                    page_title=item.get("title", ""),
                    snippet=item.get("snippet", "")
                ))
            return results
        except Exception as e:
            logger.error(f"SerpApi Baidu search failed for '{query}': {e}")
            return []
