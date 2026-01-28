"""
缓存服务层

提供统一的缓存接口，支持 Redis 和内存两种后端：
- 生产环境：使用 Redis 实现分布式缓存
- 开发环境：使用内存缓存（默认）

设计原则：
- 接口统一，后端可切换
- 支持 TTL 过期
- 异步操作
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
import structlog

from config.settings import settings

logger = structlog.get_logger()


class CacheBackend(ABC):
    """缓存后端抽象基类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """设置缓存值，ttl 单位为秒"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    @abstractmethod
    async def keys(self, pattern: str) -> list[str]:
        """获取匹配模式的所有键"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass


class MemoryCacheBackend(CacheBackend):
    """
    内存缓存后端

    适用于单进程开发环境
    """

    def __init__(self):
        self._cache: Dict[str, tuple[str, Optional[datetime]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key not in self._cache:
                return None
            value, expires_at = self._cache[key]
            if expires_at and datetime.now() > expires_at:
                del self._cache[key]
                return None
            return value

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            expires_at = datetime.now() + timedelta(seconds=ttl) if ttl else None
            self._cache[key] = (value, expires_at)
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        value = await self.get(key)
        return value is not None

    async def keys(self, pattern: str) -> list[str]:
        """简单的模式匹配（仅支持 prefix*）"""
        async with self._lock:
            # 清理过期键
            now = datetime.now()
            expired = [k for k, (_, exp) in self._cache.items() if exp and now > exp]
            for k in expired:
                del self._cache[k]

            # 模式匹配
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                return [k for k in self._cache.keys() if k.startswith(prefix)]
            return [k for k in self._cache.keys() if k == pattern]

    async def close(self) -> None:
        self._cache.clear()


class RedisCacheBackend(CacheBackend):
    """
    Redis 缓存后端

    适用于生产环境，支持分布式
    """

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: Optional[Any] = None

    async def _get_client(self):
        """延迟初始化 Redis 客户端"""
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Redis connection established", url=self._redis_url)
            except ImportError:
                logger.error("redis package not installed")
                raise
            except Exception as e:
                logger.error("Redis connection failed", error=str(e))
                raise
        return self._client

    async def get(self, key: str) -> Optional[str]:
        try:
            client = await self._get_client()
            return await client.get(key)
        except Exception as e:
            logger.warning("Redis get failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        try:
            client = await self._get_client()
            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)
            return True
        except Exception as e:
            logger.warning("Redis set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning("Redis delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning("Redis exists check failed", key=key, error=str(e))
            return False

    async def keys(self, pattern: str) -> list[str]:
        try:
            client = await self._get_client()
            return await client.keys(pattern)
        except Exception as e:
            logger.warning("Redis keys failed", pattern=pattern, error=str(e))
            return []

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


class CacheService:
    """
    统一缓存服务

    自动选择后端：
    - 配置了 REDIS_URL 且可用时使用 Redis
    - 否则使用内存缓存
    """

    def __init__(self):
        self._backend: Optional[CacheBackend] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """确保后端已初始化"""
        if self._initialized:
            return

        redis_url = settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else None

        if redis_url:
            try:
                self._backend = RedisCacheBackend(redis_url)
                # 测试连接
                await self._backend.set("_test_", "1", ttl=1)
                logger.info("Using Redis cache backend")
            except Exception as e:
                logger.warning("Redis unavailable, falling back to memory", error=str(e))
                self._backend = MemoryCacheBackend()
        else:
            logger.info("Using memory cache backend (REDIS_URL not configured)")
            self._backend = MemoryCacheBackend()

        self._initialized = True

    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        await self._ensure_initialized()
        return await self._backend.get(key)

    async def get_json(self, key: str) -> Optional[Any]:
        """获取 JSON 缓存"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        await self._ensure_initialized()
        return await self._backend.set(key, value, ttl)

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置 JSON 缓存"""
        return await self.set(key, json.dumps(value, default=str), ttl)

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        await self._ensure_initialized()
        return await self._backend.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        await self._ensure_initialized()
        return await self._backend.exists(key)

    async def keys(self, pattern: str) -> list[str]:
        """获取匹配的键"""
        await self._ensure_initialized()
        return await self._backend.keys(pattern)

    async def close(self) -> None:
        """关闭连接"""
        if self._backend:
            await self._backend.close()
            self._backend = None
            self._initialized = False

    # =========================================================================
    # 任务状态管理（专用方法）
    # =========================================================================

    TASK_PREFIX = "task:"
    TASK_TTL = 3600  # 任务状态保留 1 小时

    SSE_EVENT_PREFIX = "sse_events:"
    SSE_EVENT_TTL = 1800  # SSE 事件保留 30 分钟

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return await self.get_json(f"{self.TASK_PREFIX}{task_id}")

    async def set_task(self, task_id: str, data: Dict[str, Any]) -> bool:
        """设置任务状态"""
        return await self.set_json(f"{self.TASK_PREFIX}{task_id}", data, self.TASK_TTL)

    async def update_task(self, task_id: str, **updates) -> bool:
        """更新任务状态"""
        task = await self.get_task(task_id) or {}
        task.update(updates)
        return await self.set_task(task_id, task)

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        return await self.delete(f"{self.TASK_PREFIX}{task_id}")

    async def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务"""
        keys = await self.keys(f"{self.TASK_PREFIX}*")
        tasks = {}
        for key in keys:
            task_id = key.replace(self.TASK_PREFIX, "")
            task = await self.get_task(task_id)
            if task:
                tasks[task_id] = task
        return tasks

    # =========================================================================
    # SSE 事件管理（支持分布式）
    # =========================================================================

    async def init_sse_task(self, task_id: str, symbol: str) -> bool:
        """初始化 SSE 任务事件队列"""
        data = {
            "status": "running",
            "symbol": symbol,
            "events": [],
            "event_count": 0
        }
        return await self.set_json(f"{self.SSE_EVENT_PREFIX}{task_id}", data, self.SSE_EVENT_TTL)

    async def push_sse_event(self, task_id: str, event_type: str, event_data: Any) -> bool:
        """推送 SSE 事件"""
        key = f"{self.SSE_EVENT_PREFIX}{task_id}"
        task = await self.get_json(key)
        if not task:
            return False

        task["events"].append({
            "event": event_type,
            "data": event_data
        })
        task["event_count"] = len(task["events"])
        return await self.set_json(key, task, self.SSE_EVENT_TTL)

    async def get_sse_events(self, task_id: str, from_index: int = 0) -> Optional[Dict[str, Any]]:
        """获取 SSE 事件（从指定索引开始）"""
        key = f"{self.SSE_EVENT_PREFIX}{task_id}"
        task = await self.get_json(key)
        if not task:
            return None

        return {
            "status": task.get("status", "unknown"),
            "symbol": task.get("symbol"),
            "events": task.get("events", [])[from_index:],
            "total_events": task.get("event_count", 0)
        }

    async def set_sse_status(self, task_id: str, status: str) -> bool:
        """设置 SSE 任务状态"""
        key = f"{self.SSE_EVENT_PREFIX}{task_id}"
        task = await self.get_json(key)
        if not task:
            return False

        task["status"] = status
        return await self.set_json(key, task, self.SSE_EVENT_TTL)

    async def cleanup_sse_task(self, task_id: str) -> bool:
        """清理 SSE 任务（任务完成后延迟清理）"""
        return await self.delete(f"{self.SSE_EVENT_PREFIX}{task_id}")


# 全局单例
cache_service = CacheService()
