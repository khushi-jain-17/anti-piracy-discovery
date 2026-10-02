import pytest
from discovery.base import SearchResult
from discovery.orchestrator import SearchOrchestrator

def test_extract_domain():
    assert SearchResult.extract_domain("https://www.dazn.com/en-GLOBAL/welcome") == "dazn.com"
    assert SearchResult.extract_domain("http://vipleague.st/dazn-stream") == "vipleague.st"
    assert SearchResult.extract_domain("https://dazn-live.xyz/watch") == "dazn-live.xyz"

def test_url_normalization():
    norm = SearchOrchestrator._normalize_url
    assert norm("https://dazn.com/live/") == "dazn.com/live"
    assert norm("http://kayosports.com.au/stream") == "kayosports.com.au/stream"
