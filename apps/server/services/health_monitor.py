"""系统健康监控服务"""
import asyncio
import psutil
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from collections import deque

from config.settings import settings

logger = structlog.get_logger()


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """组件健康状态"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    last_check: datetime


class SystemMetrics(BaseModel):
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


class ErrorRecord(BaseModel):
    """错误记录"""
    timestamp: datetime
    component: str
    error_type: str
    message: str
    count: int = 1


class ProviderStatus(BaseModel):
    """数据源状态"""
    available: bool
    failure_count: int
    threshold: int
    last_failure: Optional[datetime] = None
    cooldown_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    last_error: Optional[str] = None


class HealthReport(BaseModel):
    """健康报告"""
    overall_status: HealthStatus
    components: List[ComponentHealth]
    system_metrics: SystemMetrics
    data_providers: Dict[str, ProviderStatus]
    recent_errors: List[ErrorRecord]
    uptime_seconds: float
    checked_at: datetime


class HealthMonitorService:
    """
    系统健康监控服务

    功能：
    1. 监控各组件健康状态
    2. 收集系统指标
    3. 记录和追踪错误
    4. 提供诊断 API
    5. 记录数据源调用历史（延迟、成功/失败、熔断事件）
    """

    _instance = None
    _start_time: datetime = datetime.now()
    _error_history: deque = deque(maxlen=100)  # 最近 100 条错误
    _component_cache: Dict[str, ComponentHealth] = {}
    _cache_ttl = timedelta(seconds=30)
    _last_check: Optional[datetime] = None

    # 数据源调用历史：{ provider: deque([{timestamp, latency_ms, success, error}]) }
    _provider_history: Dict[str, deque] = {}
    # 熔断事件时间线
    _circuit_breaker_events: deque = deque(maxlen=200)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        if not self._initialized:
            self._initialized = True
            self._start_time = datetime.now()
            logger.info("HealthMonitorService initialized")

    def record_error(self, component: str, error_type: str, message: str):
        """记录错误"""
        now = datetime.now()

        # 检查是否有相同的最近错误（去重）
        for error in self._error_history:
            if (error.component == component and
                error.error_type == error_type and
                error.message == message and
                (now - error.timestamp) < timedelta(minutes=5)):
                error.count += 1
                error.timestamp = now
                return

        # 添加新错误
        self._error_history.append(ErrorRecord(
            timestamp=now,
            component=component,
            error_type=error_type,
            message=message[:500]  # 限制消息长度
        ))

        logger.warning("Error recorded", component=component, error_type=error_type)

    async def check_database(self) -> ComponentHealth:
        """检查数据库健康状态"""
        start = datetime.now()
        try:
            from sqlmodel import Session, text
            from db.models import engine

            with Session(engine) as session:
                session.exec(text("SELECT 1"))

            latency = (datetime.now() - start).total_seconds() * 1000

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY if latency < 1000 else HealthStatus.DEGRADED,
                message=f"SQLite/PostgreSQL ({settings.DATABASE_MODE})",
                latency_ms=round(latency, 2),
                last_check=datetime.now()
            )

        except Exception as e:
            self.record_error("database", type(e).__name__, str(e))
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=str(e)[:200],
                last_check=datetime.now()
            )

    async def check_chromadb(self) -> ComponentHealth:
        """检查 ChromaDB 健康状态"""
        start = datetime.now()
        try:
            from services.memory_service import memory_service

            if not memory_service.is_available():
                return ComponentHealth(
                    name="chromadb",
                    status=HealthStatus.DEGRADED,
                    message="ChromaDB not initialized",
                    last_check=datetime.now()
                )

            stats = memory_service.get_stats()
            latency = (datetime.now() - start).total_seconds() * 1000

            return ComponentHealth(
                name="chromadb",
                status=HealthStatus.HEALTHY,
                message=f"Memories: {stats.get('total_memories', 0)}",
                latency_ms=round(latency, 2),
                last_check=datetime.now()
            )

        except Exception as e:
            self.record_error("chromadb", type(e).__name__, str(e))
            return ComponentHealth(
                name="chromadb",
                status=HealthStatus.UNHEALTHY,
                message=str(e)[:200],
                last_check=datetime.now()
            )

    async def check_scheduler(self) -> ComponentHealth:
        """检查调度器健康状态"""
        try:
            from services.scheduler import watchlist_scheduler

            jobs = watchlist_scheduler.get_jobs()

            if not jobs:
                return ComponentHealth(
                    name="scheduler",
                    status=HealthStatus.DEGRADED,
                    message="No scheduled jobs",
                    last_check=datetime.now()
                )

            return ComponentHealth(
                name="scheduler",
                status=HealthStatus.HEALTHY,
                message=f"Active jobs: {len(jobs)}",
                last_check=datetime.now()
            )

        except Exception as e:
            self.record_error("scheduler", type(e).__name__, str(e))
            return ComponentHealth(
                name="scheduler",
                status=HealthStatus.UNHEALTHY,
                message=str(e)[:200],
                last_check=datetime.now()
            )

    async def check_market_watcher(self) -> ComponentHealth:
        """检查市场监控服务状态"""
        try:
            from services.market_watcher import market_watcher

            stats = market_watcher.get_stats()

            if not stats.get("akshare_available") and not stats.get("yfinance_available"):
                return ComponentHealth(
                    name="market_watcher",
                    status=HealthStatus.DEGRADED,
                    message="No data providers available",
                    last_check=datetime.now()
                )

            return ComponentHealth(
                name="market_watcher",
                status=HealthStatus.HEALTHY,
                message=f"Cached indices: {stats.get('cached_indices', 0)}",
                last_check=datetime.now()
            )

        except Exception as e:
            self.record_error("market_watcher", type(e).__name__, str(e))
            return ComponentHealth(
                name="market_watcher",
                status=HealthStatus.UNHEALTHY,
                message=str(e)[:200],
                last_check=datetime.now()
            )

    async def check_news_aggregator(self) -> ComponentHealth:
        """检查新闻聚合服务状态"""
        try:
            from services.news_aggregator import news_aggregator

            stats = news_aggregator.get_stats()

            if not stats.get("feedparser_available") and not stats.get("finnhub_available"):
                return ComponentHealth(
                    name="news_aggregator",
                    status=HealthStatus.DEGRADED,
                    message="No news sources available",
                    last_check=datetime.now()
                )

            return ComponentHealth(
                name="news_aggregator",
                status=HealthStatus.HEALTHY,
                message=f"Cached news: {stats.get('cached_news', 0)}",
                last_check=datetime.now()
            )

        except Exception as e:
            self.record_error("news_aggregator", type(e).__name__, str(e))
            return ComponentHealth(
                name="news_aggregator",
                status=HealthStatus.UNHEALTHY,
                message=str(e)[:200],
                last_check=datetime.now()
            )

    async def check_llm_providers(self) -> ComponentHealth:
        """检查 LLM 提供商配置"""
        providers = []

        if settings.OPENAI_API_KEY:
            providers.append("OpenAI")
        if settings.ANTHROPIC_API_KEY:
            providers.append("Anthropic")
        if settings.GOOGLE_API_KEY:
            providers.append("Google")

        if not providers:
            return ComponentHealth(
                name="llm_providers",
                status=HealthStatus.UNHEALTHY,
                message="No LLM API keys configured",
                last_check=datetime.now()
            )

        return ComponentHealth(
            name="llm_providers",
            status=HealthStatus.HEALTHY,
            message=f"Available: {', '.join(providers)}",
            last_check=datetime.now()
        )

    def record_provider_call(
        self,
        provider: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """记录数据源调用（供 data_router 调用）

        Args:
            provider: 数据源名称 (akshare/yfinance/alpha_vantage)
            latency_ms: 调用延迟（毫秒）
            success: 是否成功
            error: 错误信息（失败时）
        """
        if provider not in self._provider_history:
            self._provider_history[provider] = deque(maxlen=500)

        record = {
            "timestamp": datetime.now().isoformat(),
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "error": error[:200] if error else None,
        }
        self._provider_history[provider].append(record)

        # 检测熔断事件：连续失败达到阈值
        if not success:
            recent_failures = sum(
                1 for r in list(self._provider_history[provider])[-5:]
                if not r["success"]
            )
            if recent_failures >= 5:
                self._circuit_breaker_events.append({
                    "timestamp": datetime.now().isoformat(),
                    "provider": provider,
                    "event": "circuit_open",
                    "message": f"{provider} 连续失败 {recent_failures} 次，触发熔断",
                })

    def get_provider_history(
        self, provider: str, minutes: int = 60
    ) -> Dict[str, Any]:
        """获取数据源调用历史

        Args:
            provider: 数据源名称
            minutes: 查询最近 N 分钟的数据

        Returns:
            包含调用记录、统计摘要和熔断事件的字典
        """
        cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()

        # 过滤时间范围内的记录
        history = self._provider_history.get(provider, deque())
        records = [r for r in history if r["timestamp"] >= cutoff]

        # 统计摘要
        total = len(records)
        successes = sum(1 for r in records if r["success"])
        failures = total - successes
        latencies = [r["latency_ms"] for r in records if r["success"]]

        summary = {
            "total_calls": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total * 100, 2) if total > 0 else 0,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 2),
            "max_latency_ms": round(max(latencies), 2) if latencies else 0,
        }

        # 相关熔断事件
        cb_events = [
            e for e in self._circuit_breaker_events
            if e["provider"] == provider and e["timestamp"] >= cutoff
        ]

        return {
            "provider": provider,
            "period_minutes": minutes,
            "records": records,
            "summary": summary,
            "circuit_breaker_events": cb_events,
        }

    def get_all_provider_histories(self) -> List[str]:
        """获取所有有记录的数据源名称"""
        return list(self._provider_history.keys())

    def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return SystemMetrics(
                cpu_percent=round(cpu_percent, 1),
                memory_percent=round(memory.percent, 1),
                memory_used_mb=round(memory.used / (1024 * 1024), 1),
                memory_total_mb=round(memory.total / (1024 * 1024), 1),
                disk_percent=round(disk.percent, 1),
                disk_used_gb=round(disk.used / (1024 * 1024 * 1024), 1),
                disk_total_gb=round(disk.total / (1024 * 1024 * 1024), 1)
            )

        except Exception as e:
            logger.warning("Failed to get system metrics", error=str(e))
            return SystemMetrics(
                cpu_percent=0,
                memory_percent=0,
                memory_used_mb=0,
                memory_total_mb=0,
                disk_percent=0,
                disk_used_gb=0,
                disk_total_gb=0
            )

    def _calculate_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """计算整体健康状态"""
        unhealthy_count = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for c in components if c.status == HealthStatus.DEGRADED)

        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > len(components) // 2:
            return HealthStatus.DEGRADED
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def get_health_report(self, force_refresh: bool = False) -> HealthReport:
        """获取完整健康报告"""
        now = datetime.now()

        # 如果缓存有效且不强制刷新，返回缓存
        if (not force_refresh and
            self._last_check and
            (now - self._last_check) < self._cache_ttl and
            self._component_cache):
            components = list(self._component_cache.values())
        else:
            # 并行检查所有组件
            checks = await asyncio.gather(
                self.check_database(),
                self.check_chromadb(),
                self.check_scheduler(),
                self.check_market_watcher(),
                self.check_news_aggregator(),
                self.check_llm_providers(),
                return_exceptions=True
            )

            components = []
            for check in checks:
                if isinstance(check, Exception):
                    components.append(ComponentHealth(
                        name="unknown",
                        status=HealthStatus.UNKNOWN,
                        message=str(check)[:200],
                        last_check=now
                    ))
                else:
                    components.append(check)

            # 更新缓存
            self._component_cache = {c.name: c for c in components}
            self._last_check = now

        # 计算运行时间
        uptime = (now - self._start_time).total_seconds()

        # 获取最近错误
        recent_errors = list(self._error_history)[-10:]

        # 获取数据源状态
        from services.data_router import MarketRouter
        data_providers = MarketRouter.get_provider_status()

        return HealthReport(
            overall_status=self._calculate_overall_status(components),
            components=components,
            system_metrics=self.get_system_metrics(),
            data_providers=data_providers,
            recent_errors=recent_errors,
            uptime_seconds=round(uptime, 1),
            checked_at=now
        )

    def get_uptime(self) -> Dict[str, Any]:
        """获取运行时间信息"""
        now = datetime.now()
        uptime = now - self._start_time

        return {
            "start_time": self._start_time.isoformat(),
            "uptime_seconds": round(uptime.total_seconds(), 1),
            "uptime_formatted": str(uptime).split('.')[0],  # 去掉微秒
            "current_time": now.isoformat()
        }

    def clear_errors(self) -> int:
        """清除错误历史"""
        count = len(self._error_history)
        self._error_history.clear()
        logger.info("Error history cleared", count=count)
        return count


# 全局单例
health_monitor = HealthMonitorService()
