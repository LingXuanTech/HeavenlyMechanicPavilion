"""
CacheService 单元测试

覆盖:
1. MemoryCacheBackend 基本操作
2. MemoryCacheBackend TTL 过期
3. MemoryCacheBackend 模式匹配
4. CacheService 初始化
5. CacheService JSON 操作
6. 任务状态管理
7. SSE 事件管理
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from services.cache_service import (
    CacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
    CacheService,
    cache_service,
)


# =============================================================================
# MemoryCacheBackend 测试
# =============================================================================

class TestMemoryCacheBackend:
    """内存缓存后端测试"""

    @pytest.fixture
    def backend(self):
        """创建后端实例"""
        return MemoryCacheBackend()

    @pytest.mark.asyncio
    async def test_set_and_get(self, backend):
        """设置和获取值"""
        await backend.set("key1", "value1")
        result = await backend.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_stats(self, backend):
        """测试统计信息"""
        await backend.set("key1", "value1")
        await backend.get("key1")  # hit
        await backend.get("key2")  # miss
        
        stats = backend.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total"] == 2
        assert stats["hit_rate"] == "50.00%"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, backend):
        """获取不存在的键返回 None"""
        result = await backend.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, backend):
        """设置带 TTL 的值"""
        await backend.set("key_ttl", "value_ttl", ttl=1)
        result = await backend.get("key_ttl")

        assert result == "value_ttl"

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, backend):
        """TTL 过期后值消失"""
        await backend.set("key_expire", "value_expire", ttl=1)

        # 等待过期
        await asyncio.sleep(1.1)

        result = await backend.get("key_expire")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self, backend):
        """删除存在的键"""
        await backend.set("key_del", "value_del")
        result = await backend.delete("key_del")

        assert result is True
        assert await backend.get("key_del") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, backend):
        """删除不存在的键"""
        result = await backend.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, backend):
        """键存在"""
        await backend.set("key_exists", "value")
        result = await backend.exists("key_exists")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, backend):
        """键不存在"""
        result = await backend.exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_after_expiry(self, backend):
        """过期后 exists 返回 False"""
        await backend.set("key_exp", "value", ttl=1)
        await asyncio.sleep(1.1)

        result = await backend.exists("key_exp")
        assert result is False

    @pytest.mark.asyncio
    async def test_keys_prefix_pattern(self, backend):
        """前缀模式匹配"""
        await backend.set("task:1", "v1")
        await backend.set("task:2", "v2")
        await backend.set("other:1", "v3")

        result = await backend.keys("task:*")

        assert len(result) == 2
        assert "task:1" in result
        assert "task:2" in result

    @pytest.mark.asyncio
    async def test_keys_exact_match(self, backend):
        """精确匹配"""
        await backend.set("exact_key", "value")

        result = await backend.keys("exact_key")

        assert result == ["exact_key"]

    @pytest.mark.asyncio
    async def test_keys_cleans_expired(self, backend):
        """keys() 清理过期键"""
        await backend.set("fresh", "value")
        await backend.set("stale", "value", ttl=1)

        await asyncio.sleep(1.5)  # 增加等待时间确保过期

        result = await backend.keys("*")

        # 只有 fresh 存在
        assert "fresh" in result
        assert "stale" not in result

    @pytest.mark.asyncio
    async def test_close(self, backend):
        """关闭清空缓存"""
        await backend.set("key", "value")
        await backend.close()

        assert len(backend._cache) == 0


# =============================================================================
# RedisCacheBackend 测试（Mock）
# =============================================================================

class TestRedisCacheBackend:
    """Redis 缓存后端测试（使用 Mock）"""

    @pytest.fixture
    def backend(self):
        """创建后端实例"""
        return RedisCacheBackend("redis://localhost:6379")

    @pytest.mark.asyncio
    async def test_get_success(self, backend):
        """获取值成功"""
        mock_client = AsyncMock()
        mock_client.get.return_value = "cached_value"

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.get("key")

        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_stats(self, backend):
        """测试统计信息"""
        mock_client = AsyncMock()
        mock_client.get.side_effect = ["value1", None]

        with patch.object(backend, '_get_client', return_value=mock_client):
            await backend.get("key1")  # hit
            await backend.get("key2")  # miss

        stats = backend.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total"] == 2
        assert stats["hit_rate"] == "50.00%"

    @pytest.mark.asyncio
    async def test_get_error_returns_none(self, backend):
        """获取失败返回 None"""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Redis error")

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.get("key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, backend):
        """设置带 TTL"""
        mock_client = AsyncMock()

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.set("key", "value", ttl=60)

        assert result is True
        mock_client.setex.assert_called_once_with("key", 60, "value")

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, backend):
        """设置不带 TTL"""
        mock_client = AsyncMock()

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.set("key", "value")

        assert result is True
        mock_client.set.assert_called_once_with("key", "value")

    @pytest.mark.asyncio
    async def test_delete_success(self, backend):
        """删除成功"""
        mock_client = AsyncMock()
        mock_client.delete.return_value = 1

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.delete("key")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, backend):
        """删除不存在的键"""
        mock_client = AsyncMock()
        mock_client.delete.return_value = 0

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.delete("key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, backend):
        """键存在"""
        mock_client = AsyncMock()
        mock_client.exists.return_value = 1

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.exists("key")

        assert result is True

    @pytest.mark.asyncio
    async def test_keys_pattern(self, backend):
        """模式匹配键"""
        mock_client = AsyncMock()
        mock_client.keys.return_value = ["task:1", "task:2"]

        with patch.object(backend, '_get_client', return_value=mock_client):
            result = await backend.keys("task:*")

        assert result == ["task:1", "task:2"]

    @pytest.mark.asyncio
    async def test_close(self, backend):
        """关闭连接"""
        mock_client = AsyncMock()
        backend._client = mock_client

        await backend.close()

        mock_client.close.assert_called_once()
        assert backend._client is None


# =============================================================================
# CacheService 测试
# =============================================================================

class TestCacheService:
    """CacheService 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例（强制使用内存后端）"""
        svc = CacheService()
        svc._backend = MemoryCacheBackend()
        svc._initialized = True
        return svc

    @pytest.mark.asyncio
    async def test_get_and_set(self, service):
        """基本 get/set"""
        await service.set("key", "value")
        result = await service.get("key")

        assert result == "value"

    @pytest.mark.asyncio
    async def test_get_json(self, service):
        """获取 JSON"""
        await service.set("json_key", '{"name": "test", "value": 123}')
        result = await service.get_json("json_key")

        assert result == {"name": "test", "value": 123}

    @pytest.mark.asyncio
    async def test_get_json_invalid(self, service):
        """获取无效 JSON 返回 None"""
        await service.set("invalid_json", "not json")
        result = await service.get_json("invalid_json")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_json_not_found(self, service):
        """获取不存在的 JSON 返回 None"""
        result = await service.get_json("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_json(self, service):
        """设置 JSON"""
        await service.set_json("json_set", {"key": "value"})
        result = await service.get("json_set")

        assert '"key": "value"' in result

    @pytest.mark.asyncio
    async def test_set_json_with_datetime(self, service):
        """设置包含 datetime 的 JSON"""
        now = datetime.now()
        await service.set_json("json_dt", {"time": now})

        result = await service.get("json_dt")
        assert result is not None  # datetime 被转换为字符串

    @pytest.mark.asyncio
    async def test_delete(self, service):
        """删除键"""
        await service.set("to_delete", "value")
        result = await service.delete("to_delete")

        assert result is True
        assert await service.get("to_delete") is None

    @pytest.mark.asyncio
    async def test_exists(self, service):
        """检查存在"""
        await service.set("exists_key", "value")

        assert await service.exists("exists_key") is True
        assert await service.exists("not_exists") is False

    @pytest.mark.asyncio
    async def test_keys(self, service):
        """获取匹配的键"""
        await service.set("prefix:1", "v1")
        await service.set("prefix:2", "v2")

        result = await service.keys("prefix:*")

        assert len(result) == 2


# =============================================================================
# 任务状态管理测试
# =============================================================================

class TestTaskManagement:
    """任务状态管理测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = CacheService()
        svc._backend = MemoryCacheBackend()
        svc._initialized = True
        return svc

    @pytest.mark.asyncio
    async def test_set_and_get_task(self, service):
        """设置和获取任务"""
        task_data = {"status": "running", "progress": 50}
        await service.set_task("task_123", task_data)

        result = await service.get_task("task_123")

        assert result["status"] == "running"
        assert result["progress"] == 50

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service):
        """获取不存在的任务"""
        result = await service.get_task("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_task(self, service):
        """更新任务状态"""
        await service.set_task("task_456", {"status": "running"})
        await service.update_task("task_456", progress=75, result="partial")

        result = await service.get_task("task_456")

        assert result["status"] == "running"
        assert result["progress"] == 75
        assert result["result"] == "partial"

    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self, service):
        """更新不存在的任务（创建新任务）"""
        await service.update_task("new_task", status="created")

        result = await service.get_task("new_task")

        assert result["status"] == "created"

    @pytest.mark.asyncio
    async def test_delete_task(self, service):
        """删除任务"""
        await service.set_task("task_del", {"status": "completed"})
        result = await service.delete_task("task_del")

        assert result is True
        assert await service.get_task("task_del") is None

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, service):
        """获取所有任务"""
        await service.set_task("task_1", {"status": "running"})
        await service.set_task("task_2", {"status": "completed"})

        result = await service.get_all_tasks()

        assert len(result) == 2
        assert "task_1" in result
        assert "task_2" in result


# =============================================================================
# SSE 事件管理测试
# =============================================================================

class TestSSEEventManagement:
    """SSE 事件管理测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = CacheService()
        svc._backend = MemoryCacheBackend()
        svc._initialized = True
        return svc

    @pytest.mark.asyncio
    async def test_init_sse_task(self, service):
        """初始化 SSE 任务"""
        result = await service.init_sse_task("sse_123", "AAPL")

        assert result is True

        data = await service.get_sse_events("sse_123")
        assert data["status"] == "running"
        assert data["symbol"] == "AAPL"
        assert data["events"] == []

    @pytest.mark.asyncio
    async def test_push_sse_event(self, service):
        """推送 SSE 事件"""
        await service.init_sse_task("sse_push", "AAPL")
        result = await service.push_sse_event("sse_push", "progress", {"stage": "analyst", "progress": 30})

        assert result is True

        data = await service.get_sse_events("sse_push")
        assert len(data["events"]) == 1
        assert data["events"][0]["event"] == "progress"
        assert data["total_events"] == 1

    @pytest.mark.asyncio
    async def test_push_multiple_events(self, service):
        """推送多个 SSE 事件"""
        await service.init_sse_task("sse_multi", "AAPL")
        await service.push_sse_event("sse_multi", "progress", {"stage": "analyst"})
        await service.push_sse_event("sse_multi", "progress", {"stage": "debate"})
        await service.push_sse_event("sse_multi", "complete", {"result": "done"})

        data = await service.get_sse_events("sse_multi")
        assert len(data["events"]) == 3
        assert data["total_events"] == 3

    @pytest.mark.asyncio
    async def test_push_event_nonexistent_task(self, service):
        """推送事件到不存在的任务"""
        result = await service.push_sse_event("nonexistent", "event", {})

        assert result is False

    @pytest.mark.asyncio
    async def test_get_events_from_index(self, service):
        """从指定索引获取事件"""
        await service.init_sse_task("sse_index", "AAPL")
        await service.push_sse_event("sse_index", "e1", {"v": 1})
        await service.push_sse_event("sse_index", "e2", {"v": 2})
        await service.push_sse_event("sse_index", "e3", {"v": 3})

        data = await service.get_sse_events("sse_index", from_index=1)

        assert len(data["events"]) == 2  # 索引 1 和 2
        assert data["events"][0]["event"] == "e2"

    @pytest.mark.asyncio
    async def test_get_events_nonexistent(self, service):
        """获取不存在任务的事件"""
        result = await service.get_sse_events("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_sse_status(self, service):
        """设置 SSE 任务状态"""
        await service.init_sse_task("sse_status", "AAPL")
        result = await service.set_sse_status("sse_status", "completed")

        assert result is True

        data = await service.get_sse_events("sse_status")
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_set_sse_status_nonexistent(self, service):
        """设置不存在任务的状态"""
        result = await service.set_sse_status("nonexistent", "completed")

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_sse_task(self, service):
        """清理 SSE 任务"""
        await service.init_sse_task("sse_cleanup", "AAPL")
        result = await service.cleanup_sse_task("sse_cleanup")

        assert result is True
        assert await service.get_sse_events("sse_cleanup") is None


# =============================================================================
# CacheService 初始化测试
# =============================================================================

class TestCacheServiceInitialization:
    """CacheService 初始化测试"""

    @pytest.mark.asyncio
    async def test_init_without_redis(self):
        """无 Redis 配置使用内存后端"""
        service = CacheService()

        with patch("services.cache_service.settings") as mock_settings:
            mock_settings.REDIS_URL = None

            await service._ensure_initialized()

        assert isinstance(service._backend, MemoryCacheBackend)
        assert service._initialized is True

        # 清理
        await service.close()

    @pytest.mark.asyncio
    async def test_init_redis_fallback(self):
        """Redis 不可用时降级到内存"""
        service = CacheService()

        with patch("services.cache_service.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"

            # 模拟 Redis 连接失败
            with patch.object(RedisCacheBackend, 'set', side_effect=Exception("Connection failed")):
                await service._ensure_initialized()

        assert isinstance(service._backend, MemoryCacheBackend)

        # 清理
        await service.close()


# =============================================================================
# 单例测试
# =============================================================================

class TestCacheServiceSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert cache_service is not None
        assert isinstance(cache_service, CacheService)
