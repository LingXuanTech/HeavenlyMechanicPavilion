"""
TaskQueue 单元测试

覆盖:
1. AnalysisTask 数据类（序列化/反序列化）
2. MemoryQueueBackend（入队、出队、确认、重试）
3. TaskQueueService（统一接口）
"""
import json
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from services.task_queue import (
    TaskStatus,
    AnalysisTask,
    MemoryQueueBackend,
    RedisQueueBackend,
    TaskQueueService,
)


# =============================================================================
# AnalysisTask 数据类测试
# =============================================================================

class TestAnalysisTask:
    """AnalysisTask 数据类测试"""

    def test_create_task_defaults(self):
        """创建任务使用默认值"""
        task = AnalysisTask(
            task_id="task-123",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
        )

        assert task.task_id == "task-123"
        assert task.symbol == "AAPL"
        assert task.analysis_level == "L2"
        assert task.use_planner is True
        assert task.override_analysts is None
        assert task.exclude_analysts is None
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_create_task_with_analysts(self):
        """创建任务指定分析师"""
        task = AnalysisTask(
            task_id="task-456",
            symbol="600519.SH",
            trade_date="2026-02-02",
            analysis_level="L1",
            use_planner=False,
            override_analysts=["market", "news"],
            exclude_analysts=["social"],
        )

        assert task.override_analysts == ["market", "news"]
        assert task.exclude_analysts == ["social"]

    def test_to_dict(self):
        """转换为字典"""
        task = AnalysisTask(
            task_id="task-789",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
            override_analysts=["market", "news"],
            exclude_analysts=None,
        )

        data = task.to_dict()

        assert data["task_id"] == "task-789"
        assert data["symbol"] == "AAPL"
        # 列表应该被 JSON 序列化
        assert data["override_analysts"] == '["market", "news"]'
        assert data["exclude_analysts"] is None

    def test_from_dict(self):
        """从字典创建"""
        data = {
            "task_id": "task-abc",
            "symbol": "MSFT",
            "trade_date": "2026-02-02",
            "analysis_level": "L1",
            "use_planner": "true",  # 字符串形式
            "override_analysts": '["fundamentals"]',  # JSON 字符串
            "exclude_analysts": None,
            "retry_count": "1",  # 字符串形式
            "max_retries": "5",
        }

        task = AnalysisTask.from_dict(data)

        assert task.task_id == "task-abc"
        assert task.symbol == "MSFT"
        assert task.use_planner is True
        assert task.override_analysts == ["fundamentals"]
        assert task.retry_count == 1
        assert task.max_retries == 5

    def test_from_dict_bool_use_planner(self):
        """从字典创建 - use_planner 为布尔值"""
        data = {
            "task_id": "task-bool",
            "symbol": "AAPL",
            "trade_date": "2026-02-02",
            "analysis_level": "L2",
            "use_planner": False,  # 布尔值
        }

        task = AnalysisTask.from_dict(data)

        assert task.use_planner is False

    def test_from_dict_string_false(self):
        """从字典创建 - use_planner 为字符串 'false'"""
        data = {
            "task_id": "task-str",
            "symbol": "AAPL",
            "trade_date": "2026-02-02",
            "analysis_level": "L2",
            "use_planner": "false",
        }

        task = AnalysisTask.from_dict(data)

        assert task.use_planner is False

    def test_roundtrip(self):
        """序列化往返测试"""
        original = AnalysisTask(
            task_id="roundtrip",
            symbol="GOOG",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
            override_analysts=["market", "fundamentals"],
            exclude_analysts=["social", "sentiment"],
            created_at="2026-02-02T10:00:00",
            retry_count=2,
            max_retries=5,
        )

        data = original.to_dict()
        restored = AnalysisTask.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.symbol == original.symbol
        assert restored.use_planner == original.use_planner
        assert restored.override_analysts == original.override_analysts
        assert restored.exclude_analysts == original.exclude_analysts
        assert restored.retry_count == original.retry_count


# =============================================================================
# MemoryQueueBackend 测试
# =============================================================================

class TestMemoryQueueBackend:
    """内存队列后端测试"""

    @pytest.fixture
    def backend(self):
        """创建内存后端实例"""
        return MemoryQueueBackend()

    @pytest.fixture
    def sample_task(self):
        """示例任务"""
        return AnalysisTask(
            task_id="mem-task-1",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
        )

    @pytest.mark.asyncio
    async def test_enqueue(self, backend, sample_task):
        """入队任务"""
        message_id = await backend.enqueue(sample_task)

        assert message_id is not None
        assert message_id.startswith("mem_")
        assert await backend.get_pending_count() == 1

    @pytest.mark.asyncio
    async def test_dequeue(self, backend, sample_task):
        """出队任务"""
        await backend.enqueue(sample_task)

        result = await backend.dequeue("worker-1", block_ms=100)

        assert result is not None
        message_id, task = result
        assert task.task_id == "mem-task-1"
        assert task.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_dequeue_timeout(self, backend):
        """出队超时返回 None"""
        result = await backend.dequeue("worker-1", block_ms=50)

        assert result is None

    @pytest.mark.asyncio
    async def test_ack(self, backend, sample_task):
        """确认任务完成"""
        await backend.enqueue(sample_task)
        result = await backend.dequeue("worker-1", block_ms=100)
        message_id, _ = result

        ack_result = await backend.ack(message_id)

        assert ack_result is True
        assert message_id not in backend._pending

    @pytest.mark.asyncio
    async def test_ack_unknown_message(self, backend):
        """确认未知消息返回 False"""
        result = await backend.ack("unknown-msg-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_nack_retry(self, backend, sample_task):
        """拒绝任务触发重试"""
        await backend.enqueue(sample_task)
        result = await backend.dequeue("worker-1", block_ms=100)
        message_id, task = result

        # 重试次数 < max_retries
        assert task.retry_count == 0

        nack_result = await backend.nack(message_id, task)

        assert nack_result is True
        # 任务应该被重新入队
        assert await backend.get_pending_count() == 1

        # 再次出队，检查重试次数
        result2 = await backend.dequeue("worker-1", block_ms=100)
        _, retried_task = result2
        assert retried_task.retry_count == 1

    @pytest.mark.asyncio
    async def test_nack_max_retries(self, backend):
        """超过最大重试次数不再入队"""
        task = AnalysisTask(
            task_id="max-retry-task",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
            retry_count=3,  # 已达到 max_retries
            max_retries=3,
        )
        await backend.enqueue(task)
        result = await backend.dequeue("worker-1", block_ms=100)
        message_id, dequeued_task = result

        nack_result = await backend.nack(message_id, dequeued_task)

        assert nack_result is True
        # 任务不应该被重新入队
        assert await backend.get_pending_count() == 0

    @pytest.mark.asyncio
    async def test_close(self, backend):
        """关闭后端（内存模式无操作）"""
        await backend.close()
        # 无异常即成功


# =============================================================================
# RedisQueueBackend 测试（模拟）
# =============================================================================

class TestRedisQueueBackend:
    """Redis 队列后端测试（使用 Mock）"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis 客户端"""
        mock = AsyncMock()
        mock.xgroup_create = AsyncMock()
        mock.xadd = AsyncMock(return_value="1234567890-0")
        mock.xreadgroup = AsyncMock(return_value=None)
        mock.xack = AsyncMock(return_value=1)
        mock.xpending_range = AsyncMock(return_value=[])
        mock.xinfo_stream = AsyncMock(return_value={"length": 5})
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    def backend(self, mock_redis):
        """创建 Redis 后端实例（Mock）"""
        backend = RedisQueueBackend("redis://localhost:6379")
        backend._redis = mock_redis
        return backend

    @pytest.mark.asyncio
    async def test_enqueue(self, backend, mock_redis):
        """入队任务到 Redis Stream"""
        task = AnalysisTask(
            task_id="redis-task-1",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
        )

        message_id = await backend.enqueue(task)

        assert message_id == "1234567890-0"
        mock_redis.xadd.assert_called_once()
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "analysis:tasks"

    @pytest.mark.asyncio
    async def test_dequeue_no_messages(self, backend, mock_redis):
        """无消息时返回 None"""
        result = await backend.dequeue("worker-1", block_ms=100)

        assert result is None
        mock_redis.xreadgroup.assert_called_once()

    @pytest.mark.asyncio
    async def test_dequeue_with_message(self, backend, mock_redis):
        """出队消息"""
        mock_redis.xreadgroup.return_value = [
            ("analysis:tasks", [
                ("1234567890-0", {
                    "task_id": "redis-task-2",
                    "symbol": "MSFT",
                    "trade_date": "2026-02-02",
                    "analysis_level": "L1",
                    "use_planner": "true",
                })
            ])
        ]

        result = await backend.dequeue("worker-1", block_ms=5000)

        assert result is not None
        message_id, task = result
        assert message_id == "1234567890-0"
        assert task.task_id == "redis-task-2"
        assert task.symbol == "MSFT"

    @pytest.mark.asyncio
    async def test_ack(self, backend, mock_redis):
        """确认消息"""
        result = await backend.ack("1234567890-0")

        assert result is True
        mock_redis.xack.assert_called_once_with(
            "analysis:tasks",
            "analysis_workers",
            "1234567890-0"
        )

    @pytest.mark.asyncio
    async def test_nack_retry(self, backend, mock_redis):
        """拒绝并重试"""
        task = AnalysisTask(
            task_id="nack-task",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
            retry_count=0,
            max_retries=3,
        )

        result = await backend.nack("1234567890-0", task)

        assert result is True
        # 应该先 ack 再重新入队
        mock_redis.xack.assert_called_once()
        assert mock_redis.xadd.call_count == 1

    @pytest.mark.asyncio
    async def test_nack_to_dlq(self, backend, mock_redis):
        """超过重试次数移入死信队列"""
        task = AnalysisTask(
            task_id="dlq-task",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
            retry_count=3,
            max_retries=3,
        )

        result = await backend.nack("1234567890-0", task)

        assert result is True
        # 应该 ack 并写入 DLQ
        mock_redis.xack.assert_called_once()
        # 第二次 xadd 是写入 DLQ
        assert mock_redis.xadd.call_count == 1
        dlq_call = mock_redis.xadd.call_args
        assert dlq_call[0][0] == "analysis:dlq"

    @pytest.mark.asyncio
    async def test_get_pending_count(self, backend, mock_redis):
        """获取待处理数量"""
        count = await backend.get_pending_count()

        assert count == 5
        mock_redis.xinfo_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, backend, mock_redis):
        """关闭连接"""
        await backend.close()

        mock_redis.close.assert_called_once()
        assert backend._redis is None


# =============================================================================
# TaskQueueService 测试
# =============================================================================

class TestTaskQueueService:
    """任务队列服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        service = TaskQueueService()
        service._backend = None
        service._initialized = False
        return service

    @pytest.mark.asyncio
    async def test_initialize_memory_backend(self, service):
        """无 Redis URL 时使用内存后端"""
        with patch("services.task_queue.settings") as mock_settings:
            mock_settings.REDIS_URL = None

            await service._ensure_initialized()

        assert service._initialized is True
        assert isinstance(service._backend, MemoryQueueBackend)

    @pytest.mark.asyncio
    async def test_initialize_redis_backend(self, service):
        """有 Redis URL 时使用 Redis 后端"""
        with patch("services.task_queue.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"

            mock_redis_backend = AsyncMock(spec=RedisQueueBackend)
            mock_redis_backend._ensure_initialized = AsyncMock()

            with patch("services.task_queue.RedisQueueBackend", return_value=mock_redis_backend):
                await service._ensure_initialized()

        assert service._initialized is True
        assert service._backend == mock_redis_backend

    @pytest.mark.asyncio
    async def test_initialize_redis_fallback(self, service):
        """Redis 连接失败时降级到内存后端"""
        with patch("services.task_queue.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"

            mock_redis_backend = MagicMock()
            mock_redis_backend._ensure_initialized = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            with patch("services.task_queue.RedisQueueBackend", return_value=mock_redis_backend):
                await service._ensure_initialized()

        assert service._initialized is True
        assert isinstance(service._backend, MemoryQueueBackend)

    @pytest.mark.asyncio
    async def test_enqueue_analysis(self, service):
        """入队分析任务"""
        service._backend = AsyncMock()
        service._backend.enqueue = AsyncMock(return_value="msg-123")
        service._initialized = True

        message_id = await service.enqueue_analysis(
            task_id="task-001",
            symbol="AAPL",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
        )

        assert message_id == "msg-123"
        service._backend.enqueue.assert_called_once()

        # 验证任务参数
        call_args = service._backend.enqueue.call_args
        task = call_args[0][0]
        assert task.task_id == "task-001"
        assert task.symbol == "AAPL"
        assert task.analysis_level == "L2"

    @pytest.mark.asyncio
    async def test_dequeue(self, service):
        """出队任务"""
        mock_task = AnalysisTask(
            task_id="task-deq",
            symbol="MSFT",
            trade_date="2026-02-02",
            analysis_level="L1",
            use_planner=False,
        )
        service._backend = AsyncMock()
        service._backend.dequeue = AsyncMock(return_value=("msg-456", mock_task))
        service._initialized = True

        result = await service.dequeue("worker-1", block_ms=1000)

        assert result is not None
        message_id, task = result
        assert message_id == "msg-456"
        assert task.symbol == "MSFT"

    @pytest.mark.asyncio
    async def test_ack(self, service):
        """确认任务"""
        service._backend = AsyncMock()
        service._backend.ack = AsyncMock(return_value=True)
        service._initialized = True

        result = await service.ack("msg-789")

        assert result is True
        service._backend.ack.assert_called_once_with("msg-789")

    @pytest.mark.asyncio
    async def test_nack(self, service):
        """拒绝任务"""
        mock_task = AnalysisTask(
            task_id="task-nack",
            symbol="GOOG",
            trade_date="2026-02-02",
            analysis_level="L2",
            use_planner=True,
        )
        service._backend = AsyncMock()
        service._backend.nack = AsyncMock(return_value=True)
        service._initialized = True

        result = await service.nack("msg-101", mock_task)

        assert result is True
        service._backend.nack.assert_called_once_with("msg-101", mock_task)

    @pytest.mark.asyncio
    async def test_get_queue_stats_memory(self, service):
        """获取队列统计（内存后端）"""
        service._backend = MemoryQueueBackend()
        service._initialized = True

        stats = await service.get_queue_stats()

        assert stats["backend"] == "memory"
        assert stats["pending_count"] == 0

    @pytest.mark.asyncio
    async def test_get_queue_stats_redis(self, service):
        """获取队列统计（Redis 后端）"""
        mock_backend = AsyncMock(spec=RedisQueueBackend)
        mock_backend.get_pending_count = AsyncMock(return_value=10)
        service._backend = mock_backend
        service._initialized = True

        stats = await service.get_queue_stats()

        assert stats["backend"] == "redis"
        assert stats["pending_count"] == 10

    @pytest.mark.asyncio
    async def test_close(self, service):
        """关闭服务"""
        service._backend = AsyncMock()
        service._backend.close = AsyncMock()
        service._initialized = True

        await service.close()

        service._backend.close.assert_called_once()


# =============================================================================
# TaskStatus 枚举测试
# =============================================================================

class TestTaskStatus:
    """任务状态枚举测试"""

    def test_status_values(self):
        """状态值"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.RETRYING.value == "retrying"

    def test_status_from_string(self):
        """从字符串创建状态"""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("completed") == TaskStatus.COMPLETED
