import logging
from typing import List, Dict, Set
from .base import SearchResult
from .yandex import YandexSearchEngine
from .baidu import BaiduSearchEngine

logger = logging.getLogger(__name__)

# Sample Query Sets as mandated by the prompt specification
SAMPLE_QUERIES = {
    "English": [
        "DAZN live stream free",
        "watch DAZN channel live",
        "DAZN 1 live online",
        "Kayo sports free stream",
        "Foxtel sports live free",
    ],
    "Russian": [
        "DAZN смотреть онлайн бесплатно",
        "DAZN прямой эфир",
    ],
    "Chinese": [
        "DAZN 直播",
        "DAZN 在线观看 免费",
    ],
    "Event-based": [
        "Moto GP live stream free",
        "Formula 1 DAZN live stream",
    ],
}

class SearchOrchestrator:
    def __init__(self):
        self.yandex = YandexSearchEngine()
        self.baidu = BaiduSearchEngine()

    def run_discovery(self, max_results_per_query: int = 10, queries_per_lang: int = 5) -> List[SearchResult]:
        """Execute discovery across Yandex and Baidu for all sample queries with deduplication."""
        all_results: List[SearchResult] = []
        seen_urls: Set[str] = set()

        for lang, query_list in SAMPLE_QUERIES.items():
            selected_queries = query_list[:queries_per_lang]
            for query in selected_queries:
                # 1. Run Yandex Search
                yandex_results = self.yandex.search(query, max_results=max_results_per_query)
                for res in yandex_results:
                    clean_url = self._normalize_url(res.url)
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        all_results.append(res)

                # 2. Run Baidu Search
                baidu_results = self.baidu.search(query, max_results=max_results_per_query)
                for res in baidu_results:
                    clean_url = self._normalize_url(res.url)
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        all_results.append(res)

        logger.info(f"Discovery complete. Total unique URLs discovered: {len(all_results)}")
        return all_results

    @staticmethod
    def _normalize_url(url: str) -> str:
        url = url.strip().rstrip("/")
        if url.startswith("https://"):
            url = url[8:]
        elif url.startswith("http://"):
            url = url[7:]
        return url
