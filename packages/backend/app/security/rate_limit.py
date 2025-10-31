"""Rate limiting utilities using Redis."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, Request, status

from ..cache import get_redis_manager
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """Redis-based rate limiter."""

    def __init__(self):
        self.redis = None

    async def _get_redis(self):
        """Get Redis manager instance."""
        if self.redis is None:
            self.redis = get_redis_manager()
        return self.redis

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int,
        request: Optional[Request] = None,
    ) -> bool:
        """Check if request is within rate limit.

        Args:
            identifier: Unique identifier (user_id, api_key, ip_address)
            limit: Maximum number of requests
            window: Time window in seconds
            request: Optional FastAPI request

        Returns:
            True if within limit, False otherwise

        Raises:
            HTTPException: If rate limit exceeded
        """
        if not settings.rate_limit_enabled or not settings.redis_enabled:
            return True

        try:
            redis = await self._get_redis()
            if not redis:
                logger.warning("Redis not available, skipping rate limit check")
                return True

            key = f"rate_limit:{identifier}:{window}"
            current = await redis.get(key)

            if current is None:
                await redis.setex(key, window, 1)
                return True

            current_count = int(current)
            if current_count >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {limit} requests per {window} seconds.",
                    headers={"Retry-After": str(window)},
                )

            await redis.incr(key)
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True

    async def reset_rate_limit(self, identifier: str, window: int):
        """Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier
            window: Time window in seconds
        """
        try:
            redis = await self._get_redis()
            if redis:
                key = f"rate_limit:{identifier}:{window}"
                await redis.delete(key)
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")

    async def get_rate_limit_info(self, identifier: str, window: int) -> dict:
        """Get rate limit information for an identifier.

        Args:
            identifier: Unique identifier
            window: Time window in seconds

        Returns:
            Dictionary with rate limit info
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return {"available": True, "current": 0, "limit": 0}

            key = f"rate_limit:{identifier}:{window}"
            current = await redis.get(key)
            ttl = await redis.ttl(key)

            return {
                "current": int(current) if current else 0,
                "window": window,
                "resets_in": ttl if ttl > 0 else window,
            }
        except Exception as e:
            logger.error(f"Error getting rate limit info: {e}")
            return {"available": True, "current": 0, "limit": 0}


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def check_user_rate_limit(user_id: int, request: Optional[Request] = None) -> bool:
    """Check rate limit for a user.

    Args:
        user_id: User ID
        request: Optional FastAPI request

    Returns:
        True if within limit
    """
    limiter = get_rate_limiter()

    await limiter.check_rate_limit(
        identifier=f"user:{user_id}",
        limit=settings.rate_limit_per_minute,
        window=60,
        request=request,
    )

    await limiter.check_rate_limit(
        identifier=f"user:{user_id}:hour",
        limit=settings.rate_limit_per_hour,
        window=3600,
        request=request,
    )

    return True


async def check_ip_rate_limit(ip_address: str, request: Optional[Request] = None) -> bool:
    """Check rate limit for an IP address.

    Args:
        ip_address: IP address
        request: Optional FastAPI request

    Returns:
        True if within limit
    """
    limiter = get_rate_limiter()

    await limiter.check_rate_limit(
        identifier=f"ip:{ip_address}",
        limit=settings.rate_limit_per_minute * 2,
        window=60,
        request=request,
    )

    return True
