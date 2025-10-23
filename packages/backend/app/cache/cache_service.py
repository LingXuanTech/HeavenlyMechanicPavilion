"""Cache service layer for high-level caching operations."""

from __future__ import annotations

from typing import Any, Optional

from .redis_client import RedisManager


class CacheService:
    """High-level cache service for application data."""

    def __init__(self, redis_manager: RedisManager):
        """Initialize the cache service.
        
        Args:
            redis_manager: The Redis manager instance
        """
        self.redis = redis_manager

    # Market data cache
    async def get_market_data(
        self, symbol: str, date: str
    ) -> Optional[dict[str, Any]]:
        """Get cached market data for a symbol and date.
        
        Args:
            symbol: Stock symbol
            date: Date string
            
        Returns:
            Market data dict or None if not cached
        """
        key = f"market_data:{symbol}:{date}"
        return await self.redis.get_json(key)

    async def cache_market_data(
        self,
        symbol: str,
        date: str,
        data: dict[str, Any],
        expire: int = 3600,
    ) -> bool:
        """Cache market data for a symbol and date.
        
        Args:
            symbol: Stock symbol
            date: Date string
            data: Market data to cache
            expire: Expiration time in seconds (default: 1 hour)
            
        Returns:
            True if successful
        """
        key = f"market_data:{symbol}:{date}"
        return await self.redis.set_json(key, data, expire)

    # Session cache
    async def get_session_data(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get cached session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data dict or None if not cached
        """
        key = f"session:{session_id}"
        return await self.redis.get_json(key)

    async def cache_session_data(
        self,
        session_id: str,
        data: dict[str, Any],
        expire: int = 86400,
    ) -> bool:
        """Cache session data.
        
        Args:
            session_id: Session ID
            data: Session data to cache
            expire: Expiration time in seconds (default: 24 hours)
            
        Returns:
            True if successful
        """
        key = f"session:{session_id}"
        return await self.redis.set_json(key, data, expire)

    async def delete_session_data(self, session_id: str) -> bool:
        """Delete cached session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted
        """
        key = f"session:{session_id}"
        return await self.redis.delete(key) > 0

    # Agent config cache
    async def get_agent_config(self, config_name: str) -> Optional[dict[str, Any]]:
        """Get cached agent configuration.
        
        Args:
            config_name: Configuration name
            
        Returns:
            Config dict or None if not cached
        """
        key = f"agent_config:{config_name}"
        return await self.redis.get_json(key)

    async def cache_agent_config(
        self,
        config_name: str,
        config: dict[str, Any],
        expire: int = 7200,
    ) -> bool:
        """Cache agent configuration.
        
        Args:
            config_name: Configuration name
            config: Configuration data to cache
            expire: Expiration time in seconds (default: 2 hours)
            
        Returns:
            True if successful
        """
        key = f"agent_config:{config_name}"
        return await self.redis.set_json(key, config, expire)

    # Generic cache operations
    async def get_cached(self, key: str) -> Optional[Any]:
        """Get a generic cached value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        return await self.redis.get_json(key)

    async def cache_value(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
    ) -> bool:
        """Cache a generic value.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
            
        Returns:
            True if successful
        """
        return await self.redis.set_json(key, value, expire)

    async def invalidate(self, key: str) -> bool:
        """Invalidate (delete) a cached value.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted
        """
        return await self.redis.delete(key) > 0
