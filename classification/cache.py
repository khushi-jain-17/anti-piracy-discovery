import json
import logging
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class RedisDomainCache:
    """
    Redis caching and deduplication layer for domain classifications.
    Provides 24-hour TTL caching for known official, defunct, or verified pirate domains.
    Falls back gracefully to an in-memory dictionary if Redis is offline or not configured.
    """
    _shared_in_memory_cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: Optional[int] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.ttl = ttl_seconds if ttl_seconds is not None else settings.REDIS_CACHE_TTL_SEC
        self.prefix = "dazn:domain:"
        self._redis_client = None
        self._in_memory_cache = self._shared_in_memory_cache
        self.hits = 0
        self.misses = 0

        self._init_connection()

    def _init_connection(self):
        try:
            import redis
            client = redis.from_url(self.redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
            # Test connection with ping
            client.ping()
            self._redis_client = client
            logger.info(f"[RedisCache] Connected successfully to Redis at {self.redis_url}")
        except Exception as e:
            logger.info(f"[RedisCache] Redis server not reachable ({e}). Using in-memory fallback cache.")
            self._redis_client = None

    @property
    def is_connected(self) -> bool:
        """Check if active connection to Redis exists."""
        if self._redis_client is None:
            return False
        try:
            return bool(self._redis_client.ping())
        except Exception:
            return False

    def _make_key(self, domain: str) -> str:
        return f"{self.prefix}{domain.lower().strip()}"

    def get(self, domain: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached classification record for domain."""
        norm_domain = domain.lower().strip()
        key = self._make_key(norm_domain)

        # 1. Try Redis
        if self._redis_client:
            try:
                raw = self._redis_client.get(key)
                if raw:
                    self.hits += 1
                    logger.debug(f"[RedisCache] HIT (Redis) for domain: {norm_domain}")
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"[RedisCache] Read error from Redis: {e}")

        # 2. Check in-memory fallback
        if norm_domain in self._in_memory_cache:
            self.hits += 1
            logger.debug(f"[RedisCache] HIT (In-Memory) for domain: {norm_domain}")
            return self._in_memory_cache[norm_domain]

        self.misses += 1
        return None

    def set(self, domain: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store classification result in Redis with TTL (default 24h)."""
        norm_domain = domain.lower().strip()
        key = self._make_key(norm_domain)
        expire_sec = ttl if ttl is not None else self.ttl

        # Save to in-memory fallback always
        self._in_memory_cache[norm_domain] = data

        if self._redis_client:
            try:
                serialized = json.dumps(data, ensure_ascii=False)
                self._redis_client.set(key, serialized, ex=expire_sec)
                logger.debug(f"[RedisCache] Saved domain {norm_domain} in Redis (TTL: {expire_sec}s)")
                return True
            except Exception as e:
                logger.warning(f"[RedisCache] Write error to Redis: {e}")
                return False
        return True

    def clear(self) -> bool:
        """Clear domain cache."""
        self._in_memory_cache.clear()
        if self._redis_client:
            try:
                keys = self._redis_client.keys(f"{self.prefix}*")
                if keys:
                    self._redis_client.delete(*keys)
                return True
            except Exception as e:
                logger.warning(f"[RedisCache] Clear error: {e}")
                return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Return cache hit/miss statistics and backend type."""
        backend = "Redis" if self.is_connected else "In-Memory Fallback"
        total_requests = self.hits + self.misses
        hit_ratio = (self.hits / total_requests) if total_requests > 0 else 0.0
        return {
            "backend": backend,
            "connected": self.is_connected,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_ratio": round(hit_ratio, 2)
        }
