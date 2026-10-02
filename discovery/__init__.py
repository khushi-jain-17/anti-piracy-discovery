"""Discovery package for retrieving and deduplicating search results."""
from .base import SearchResult, BaseSearchEngine
from .yandex import YandexSearchEngine
from .baidu import BaiduSearchEngine
from .orchestrator import SearchOrchestrator

__all__ = [
    "SearchResult",
    "BaseSearchEngine",
    "YandexSearchEngine",
    "BaiduSearchEngine",
    "SearchOrchestrator",
]
