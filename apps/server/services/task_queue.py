"""Task Queue Service

使用 Redis Stream 实现分布式任务队列，支持：
- 任务持久化
- 消费者组（支持多 worker 水平扩展）
- 任务确认（ACK）和重试
- 死信队列（DLQ）处理

设计：
- 内存模式：开发环境，使用 asyncio.Queue 模拟
- Redis 模式：生产环境，使用 Redis Stream
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional

import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AnalysisTask:
    """分析任务数据结构"""
    task_id: str
    symbol: str
    trade_date: str
    analysis_level: Literal["L1", "L2"]
    use_planner: bool
    override_analysts: Optional[List[str]] = None
    exclude_analysts: Optional[List[str]] = None
    created_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        data = asdict(self)
        if data["override_analysts"]:
            data["override_analysts"] = json.dumps(data["override_analysts"])
        if data["exclude_analysts"]:
            data["exclude_analysts"] = json.dumps(data["exclude_analysts"])
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisTask":
        """从字典创建实例"""
        if isinstance(data.get("override_analysts"), str):
            data["override_analysts"] = json.loads(data["override_analysts"]) if data["override_analysts"] else None
        if isinstance(data.get("exclude_analysts"), str):
            data["exclude_analysts"] = json.loads(data["exclude_analysts"]) if data["exclude_analysts"] else None
        data["retry_count"] = int(data.get("retry_count", 0))
        data["max_retries"] = int(data.get("max_retries", 3))
        data["use_planner"] = data.get("use_planner", "true").lower() == "true" if isinstance(data.get("use_planner"), str) else data.get("use_planner", True)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TaskQueueBackend(ABC):
    """任务队列后端抽象"""

    @abstractmethod
    async def enqueue(self, task: AnalysisTask) -> str:
        """入队任务，返回消息 ID"""
        pass

    @abstractmethod
    async def dequeue(self, consumer_name: str, block_ms: int = 5000) -> Optional[tuple[str, AnalysisTask]]:
        """出队任务，返回 (消息ID, 任务)。阻塞直到有任务或超时。"""
        pass

    @abstractmethod
    async def ack(self, message_id: str) -> bool:
        """确认任务完成"""
        pass

    @abstractmethod
    async def nack(self, message_id: str, task: AnalysisTask) -> bool:
        """拒绝任务（失败或需要重试）"""
        pass

    @abstractmethod
    async def get_pending_count(self) -> int:
        """获取待处理任务数量"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass


class MemoryQueueBackend(TaskQueueBackend):
    """内存队列后端（开发环境）"""

    def __init__(self):
        self._queue: asyncio.Queue[tuple[str, AnalysisTask]] = asyncio.Queue()
        self._pending: Dict[str, AnalysisTask] = {}

    async def enqueue(self, task: AnalysisTask) -> str:
        message_id = f"mem_{uuid.uuid4().hex[:12]}"
        await self._queue.put((message_id, task))
        logger.debug("Task enqueued to memory queue", task_id=task.task_id, message_id=message_id)
        return message_id

    async def dequeue(self, consumer_name: str, block_ms: int = 5000) -> Optional[tuple[str, AnalysisTask]]:
        try:
            message_id, task = await asyncio.wait_for(
                self._queue.get(),
                timeout=block_ms / 1000
            )
            self._pending[message_id] = task
            logger.debug("Task dequeued from memory queue", task_id=task.task_id, consumer=consumer_name)
            return message_id, task
        except asyncio.TimeoutError:
            return None

    async def ack(self, message_id: str) -> bool:
        if message_id in self._pending:
            del self._pending[message_id]
            return True
        return False

    async def nack(self, message_id: str, task: AnalysisTask) -> bool:
        if message_id in self._pending:
            del self._pending[message_id]
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await self.enqueue(task)
                logger.info("Task re-enqueued for retry", task_id=task.task_id, retry=task.retry_count)
            else:
                logger.error("Task max retries exceeded", task_id=task.task_id)
            return True
        return False

    async def get_pending_count(self) -> int:
        return self._queue.qsize()

    async def close(self) -> None:
        pass


class RedisQueueBackend(TaskQueueBackend):
    """Redis Stream 队列后端（生产环境）"""

    STREAM_KEY = "analysis:tasks"
    GROUP_NAME = "analysis_workers"
    DLQ_KEY = "analysis:dlq"

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis = None

    async def _ensure_initialized(self):
        """延迟初始化 Redis 客户端"""
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 创建消费者组（如果不存在）
            try:
                await self._redis.xgroup_create(
                    self.STREAM_KEY,
                    self.GROUP_NAME,
                    id="0",
                    mkstream=True
                )
                logger.info("Created Redis consumer group", group=self.GROUP_NAME)
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    raise
                # Group already exists, ignore

    async def enqueue(self, task: AnalysisTask) -> str:
        await self._ensure_initialized()
        message_id = await self._redis.xadd(
            self.STREAM_KEY,
            task.to_dict(),
            maxlen=10000  # 保留最近 10000 条消息
        )
        logger.info("Task enqueued to Redis Stream", task_id=task.task_id, message_id=message_id)
        return message_id

    async def dequeue(self, consumer_name: str, block_ms: int = 5000) -> Optional[tuple[str, AnalysisTask]]:
        await self._ensure_initialized()

        # 先尝试获取待确认的消息（崩溃恢复）
        pending = await self._redis.xpending_range(
            self.STREAM_KEY,
            self.GROUP_NAME,
            min="-",
            max="+",
            count=1,
            consumername=consumer_name
        )
        if pending:
            # 认领超时的消息（超过 5 分钟未确认）
            for p in pending:
                if p["time_since_delivered"] > 300000:  # 5 分钟
                    claimed = await self._redis.xclaim(
                        self.STREAM_KEY,
                        self.GROUP_NAME,
                        consumer_name,
                        min_idle_time=300000,
                        message_ids=[p["message_id"]]
                    )
                    if claimed:
                        message_id, fields = claimed[0]
                        task = AnalysisTask.from_dict(fields)
                        logger.warning("Claimed stale message", task_id=task.task_id, message_id=message_id)
                        return message_id, task

        # 读取新消息
        result = await self._redis.xreadgroup(
            groupname=self.GROUP_NAME,
            consumername=consumer_name,
            streams={self.STREAM_KEY: ">"},
            count=1,
            block=block_ms
        )

        if result:
            stream_name, messages = result[0]
            if messages:
                message_id, fields = messages[0]
                task = AnalysisTask.from_dict(fields)
                logger.debug("Task dequeued from Redis Stream", task_id=task.task_id, consumer=consumer_name)
                return message_id, task

        return None

    async def ack(self, message_id: str) -> bool:
        await self._ensure_initialized()
        result = await self._redis.xack(self.STREAM_KEY, self.GROUP_NAME, message_id)
        return result > 0

    async def nack(self, message_id: str, task: AnalysisTask) -> bool:
        await self._ensure_initialized()

        # 先确认以移出 pending 列表
        await self._redis.xack(self.STREAM_KEY, self.GROUP_NAME, message_id)

        if task.retry_count < task.max_retries:
            # 重新入队
            task.retry_count += 1
            await self.enqueue(task)
            logger.info("Task re-enqueued for retry", task_id=task.task_id, retry=task.retry_count)
        else:
            # 移入死信队列
            await self._redis.xadd(
                self.DLQ_KEY,
                {
                    **task.to_dict(),
                    "failed_at": datetime.utcnow().isoformat(),
                    "original_message_id": message_id,
                }
            )
            logger.error("Task moved to DLQ", task_id=task.task_id)

        return True

    async def get_pending_count(self) -> int:
        await self._ensure_initialized()
        info = await self._redis.xinfo_stream(self.STREAM_KEY)
        return info.get("length", 0)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


class TaskQueueService:
    """任务队列服务（统一接口）"""

    def __init__(self):
        self._backend: Optional[TaskQueueBackend] = None
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return

        redis_url = settings.REDIS_URL if hasattr(settings, "REDIS_URL") else None

        if redis_url:
            try:
                self._backend = RedisQueueBackend(redis_url)
                # 测试连接
                await self._backend._ensure_initialized()
                logger.info("Using Redis Stream task queue")
            except Exception as e:
                logger.warning("Redis unavailable, falling back to memory queue", error=str(e))
                self._backend = MemoryQueueBackend()
        else:
            logger.info("Using memory task queue (REDIS_URL not configured)")
            self._backend = MemoryQueueBackend()

        self._initialized = True

    async def enqueue_analysis(
        self,
        task_id: str,
        symbol: str,
        trade_date: str,
        analysis_level: Literal["L1", "L2"] = "L2",
        use_planner: bool = True,
        override_analysts: Optional[List[str]] = None,
        exclude_analysts: Optional[List[str]] = None,
    ) -> str:
        """入队分析任务"""
        await self._ensure_initialized()

        task = AnalysisTask(
            task_id=task_id,
            symbol=symbol,
            trade_date=trade_date,
            analysis_level=analysis_level,
            use_planner=use_planner,
            override_analysts=override_analysts,
            exclude_analysts=exclude_analysts,
            created_at=datetime.utcnow().isoformat(),
        )

        return await self._backend.enqueue(task)

    async def dequeue(self, consumer_name: str, block_ms: int = 5000) -> Optional[tuple[str, AnalysisTask]]:
        """出队任务"""
        await self._ensure_initialized()
        return await self._backend.dequeue(consumer_name, block_ms)

    async def ack(self, message_id: str) -> bool:
        """确认任务完成"""
        await self._ensure_initialized()
        return await self._backend.ack(message_id)

    async def nack(self, message_id: str, task: AnalysisTask) -> bool:
        """拒绝任务（用于重试）"""
        await self._ensure_initialized()
        return await self._backend.nack(message_id, task)

    async def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        await self._ensure_initialized()
        return {
            "pending_count": await self._backend.get_pending_count(),
            "backend": "redis" if isinstance(self._backend, RedisQueueBackend) else "memory",
        }

    async def close(self) -> None:
        """关闭连接"""
        if self._backend:
            await self._backend.close()


# 全局单例
task_queue = TaskQueueService()
