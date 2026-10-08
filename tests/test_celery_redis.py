import pytest
from unittest.mock import MagicMock, patch
from config import settings
from classification.cache import RedisDomainCache
from celery_app import app
from tasks.verification import verify_url_task

@pytest.fixture(autouse=True)
def clean_cache():
    RedisDomainCache().clear()
    yield
    RedisDomainCache().clear()

def test_redis_domain_cache_in_memory_fallback():
    """Verify cache works properly even if Redis server is offline (in-memory fallback)."""
    cache = RedisDomainCache(redis_url="redis://nonexistent:9999/0", ttl_seconds=3600)
    assert cache.is_connected is False

    test_data = {
        "domain": "test-pirate.xyz",
        "classification": "Pirate",
        "confidence_score": 85,
        "player_detected": True,
        "player_status": "Player Present - Playing"
    }

    # Cache miss
    assert cache.get("test-pirate.xyz") is None
    assert cache.misses == 1

    # Cache set & hit
    cache.set("test-pirate.xyz", test_data)
    cached = cache.get("test-pirate.xyz")
    assert cached is not None
    assert cached["classification"] == "Pirate"
    assert cache.hits == 1

    stats = cache.get_stats()
    assert stats["backend"] == "In-Memory Fallback"
    assert stats["hits"] == 1
    assert stats["misses"] == 1

def test_redis_domain_cache_with_mocked_redis():
    """Verify RedisDomainCache correctly uses Redis client when connected."""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = '{"classification": "Official", "confidence_score": 95}'

    with patch("redis.from_url", return_value=mock_redis):
        cache = RedisDomainCache(redis_url="redis://localhost:6379/0", ttl_seconds=86400)
        assert cache.is_connected is True

        res = cache.get("mock-domain.com")
        assert res["classification"] == "Official"
        mock_redis.get.assert_called_with("dazn:domain:mock-domain.com")

        # Test set
        cache.set("mock-domain.com", {"classification": "Official"}, ttl=120)
        assert mock_redis.set.called

def test_celery_app_configuration():
    """Verify Celery application name, configuration, and registered tasks."""
    assert app.main == "dazn_anti_piracy"
    assert "tasks.verify_url_task" in app.tasks
    assert app.conf.task_serializer == "json"
    assert app.conf.worker_prefetch_multiplier == 1

def test_verify_url_task_official_fast_path():
    """Verify official allowlisted domains are fast-pathed without opening browser."""
    item = {
        "search_engine": "Yandex",
        "query": "watch DAZN channel live",
        "rank": 1,
        "url": "https://www.dazn.com/en-GLOBAL/welcome",
        "domain": "dazn.com",
        "classification": "Official",
        "confidence_score": 95,
        "hosting_ip": "18.239.111.84",
        "asn": "AS16509 Amazon.com, Inc.",
        "matched_heuristics": "ALLOWLIST_MATCH"
    }

    # Run the task directly (simulating worker execution)
    result = verify_url_task(item)
    assert result["classification"] == "Official"
    assert result["player_status"] == "Not Applicable (Official)"
    assert result["player_detected"] is False

def test_verify_url_task_cache_hit_bypass():
    """Verify that cached domains bypass browser inspection."""
    cache = RedisDomainCache()
    pre_cached = {
        "search_engine": "Baidu",
        "query": "cached query",
        "rank": 1,
        "url": "https://pre-verified-pirate.xyz/watch",
        "domain": "pre-verified-pirate.xyz",
        "classification": "Pirate",
        "confidence_score": 90,
        "player_detected": True,
        "player_type": "hls.js",
        "player_status": "Player Present - Playing",
        "stream_source": "https://pre-verified-pirate.xyz/live.m3u8",
        "screenshot_path": "outputs/screenshots/dummy.png",
        "checked_at_utc": "2026-10-04 12:00:00",
        "hosting_ip": "1.2.3.4",
        "asn": "AS12345 Host",
        "matched_heuristics": "PIRACY_KEYWORD",
        "telegram_links": "None",
        "logo_match": False,
        "logo_match_details": "No match",
        "logo_match_similarity": 0.0,
    }
    cache.set("pre-verified-pirate.xyz", pre_cached)

    new_request = {
        "search_engine": "Yandex",
        "query": "new search query",
        "rank": 3,
        "url": "https://pre-verified-pirate.xyz/watch",
        "domain": "pre-verified-pirate.xyz",
        "classification": "Pirate",
        "confidence_score": 90,
    }

    result = verify_url_task(new_request)
    assert result["player_status"] == "Player Present - Playing"
    assert result["stream_source"] == "https://pre-verified-pirate.xyz/live.m3u8"
    assert result["search_engine"] == "Yandex"  # Updated with current query context
    assert result["query"] == "new search query"
