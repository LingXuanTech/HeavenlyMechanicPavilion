"""Redis client management for caching and pub/sub."""

from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as redis


class RedisManager:
    """Manages Redis connections for caching and pub/sub with connection pooling."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        max_connections: int = 50,
        socket_keepalive: bool = True,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
    ):
        """Initialize the Redis manager with connection pooling.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
            decode_responses: Whether to decode responses as strings
            max_connections: Maximum number of connections in the pool
            socket_keepalive: Enable TCP keepalive
            socket_connect_timeout: Socket connection timeout in seconds
            retry_on_timeout: Retry operations on timeout
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        
        # Create connection pool for better performance
        self._pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
            max_connections=max_connections,
            socket_keepalive=socket_keepalive,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
        )
        
        self._client: Optional[redis.Redis] = None
        self._pubsub_client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        """Get or create the Redis client with connection pooling."""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client

    @property
    def pubsub_client(self) -> redis.Redis:
        """Get or create a separate Redis client for pub/sub."""
        if self._pubsub_client is None:
            # Pub/sub uses a separate connection not from the pool
            self._pubsub_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
            )
        return self._pubsub_client

    async def ping(self) -> bool:
        """Check if Redis is accessible.

        Returns:
            True if Redis responds to ping, False otherwise
        """
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close Redis connections and connection pool."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        if self._pubsub_client is not None:
            await self._pubsub_client.close()
            self._pubsub_client = None
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None

    # Cache operations
    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache.

        Args:
            key: Cache key

        Returns:
            The cached value or None if not found
        """
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None,
    ) -> bool:
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds

        Returns:
            True if successful
        """
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            Number of keys deleted
        """
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        return await self.client.exists(key) > 0

    # JSON operations
    async def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON value from cache.

        Args:
            key: Cache key

        Returns:
            The deserialized value or None if not found
        """
        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
    ) -> bool:
        """Set a JSON value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expire: Expiration time in seconds

        Returns:
            True if successful
        """
        json_value = json.dumps(value)
        return await self.set(key, json_value, expire)

    # Pub/Sub operations (placeholder for future implementation)
    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel.

        Args:
            channel: Channel name
            message: Message to publish

        Returns:
            Number of subscribers that received the message
        """
        return await self.pubsub_client.publish(channel, message)

    async def subscribe(self, *channels: str):
        """Subscribe to channels (placeholder).

        Args:
            channels: Channel names to subscribe to

        Returns:
            PubSub object for receiving messages
        """
        pubsub = self.pubsub_client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def init_redis(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
) -> RedisManager:
    """Initialize the global Redis manager.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password (if required)

    Returns:
        RedisManager: The initialized Redis manager
    """
    global _redis_manager
    _redis_manager = RedisManager(host, port, db, password)
    return _redis_manager


def get_redis_manager() -> Optional[RedisManager]:
    """Get the global Redis manager instance.

    Returns:
        RedisManager: The Redis manager or None if not initialized
    """
    return _redis_manager
