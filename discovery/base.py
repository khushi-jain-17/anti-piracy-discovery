from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel, Field
import tldextract

class SearchResult(BaseModel):
    query: str
    search_engine: str
    rank: int
    url: str
    domain: str
    page_title: str = ""
    snippet: str = ""

    @staticmethod
    def extract_domain(url: str) -> str:
        extracted = tldextract.extract(url)
        top_dom = getattr(extracted, "top_domain_under_public_suffix", None) or getattr(extracted, "registered_domain", "")
        if top_dom:
            return top_dom.lower()
        return extracted.domain.lower() if extracted.domain else url

class BaseSearchEngine(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Execute a search query and return standardized search results."""
        pass
