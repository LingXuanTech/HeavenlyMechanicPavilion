"""
HealthMonitorService 单元测试

覆盖:
1. 数据模型创建
2. 错误记录
3. 系统指标获取
4. 组件健康检查
5. 整体状态计算
6. 健康报告
7. 运行时间
8. 单例模式
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from services.health_monitor import (
    HealthMonitorService,
    HealthStatus,
    ComponentHealth,
    SystemMetrics,
    ErrorRecord,
    HealthReport,
    health_monitor,
)


# =============================================================================
# 数据模型测试
# =============================================================================

class TestHealthModels:
    """健康数据模型测试"""

    def test_health_status_values(self):
        """HealthStatus 枚举值"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_component_health_creation(self):
        """创建 ComponentHealth"""
        health = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="SQLite OK",
            latency_ms=5.2,
            last_check=datetime.now(),
        )

        assert health.name == "database"
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 5.2

    def test_component_health_minimal(self):
        """创建最小 ComponentHealth"""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.UNKNOWN,
            last_check=datetime.now(),
        )

        assert health.message is None
        assert health.latency_ms is None

    def test_system_metrics_creation(self):
        """创建 SystemMetrics"""
        metrics = SystemMetrics(
            cpu_percent=25.5,
            memory_percent=60.0,
            memory_used_mb=4096.0,
            memory_total_mb=8192.0,
            disk_percent=50.0,
            disk_used_gb=100.0,
            disk_total_gb=200.0,
        )

        assert metrics.cpu_percent == 25.5
        assert metrics.memory_percent == 60.0

    def test_error_record_creation(self):
        """创建 ErrorRecord"""
        error = ErrorRecord(
            timestamp=datetime.now(),
            component="database",
            error_type="ConnectionError",
            message="Failed to connect",
            count=3,
        )

        assert error.component == "database"
        assert error.count == 3

    def test_health_report_creation(self):
        """创建 HealthReport"""
        report = HealthReport(
            overall_status=HealthStatus.HEALTHY,
            components=[],
            system_metrics=SystemMetrics(
                cpu_percent=10, memory_percent=50,
                memory_used_mb=4000, memory_total_mb=8000,
                disk_percent=30, disk_used_gb=50, disk_total_gb=200,
            ),
            recent_errors=[],
            uptime_seconds=3600.0,
            checked_at=datetime.now(),
        )

        assert report.overall_status == HealthStatus.HEALTHY
        assert report.uptime_seconds == 3600.0


# =============================================================================
# 错误记录测试
# =============================================================================

class TestRecordError:
    """错误记录测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(HealthMonitorService)
        svc._initialized = True
        svc._start_time = datetime.now()
        svc._error_history = HealthMonitorService._error_history.__class__(maxlen=100)
        svc._component_cache = {}
        svc._last_check = None
        return svc

    def test_record_new_error(self, service):
        """记录新错误"""
        service.record_error("database", "ConnectionError", "Connection failed")

        assert len(service._error_history) == 1
        error = service._error_history[0]
        assert error.component == "database"
        assert error.error_type == "ConnectionError"
        assert error.count == 1

    def test_record_duplicate_error(self, service):
        """记录重复错误（增加计数）"""
        service.record_error("database", "ConnectionError", "Connection failed")
        service.record_error("database", "ConnectionError", "Connection failed")

        # 应该只有一条记录，但计数为 2
        assert len(service._error_history) == 1
        assert service._error_history[0].count == 2

    def test_record_different_errors(self, service):
        """记录不同错误"""
        service.record_error("database", "ConnectionError", "Connection failed")
        service.record_error("chromadb", "TimeoutError", "Timeout")

        assert len(service._error_history) == 2

    def test_record_error_message_truncation(self, service):
        """错误消息截断"""
        long_message = "A" * 1000
        service.record_error("test", "Error", long_message)

        assert len(service._error_history[0].message) <= 500


# =============================================================================
# 系统指标测试
# =============================================================================

class TestGetSystemMetrics:
    """系统指标获取测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(HealthMonitorService)
        svc._initialized = True
        return svc

    def test_get_metrics_success(self, service):
        """成功获取系统指标"""
        mock_memory = MagicMock()
        mock_memory.percent = 65.5
        mock_memory.used = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory.total = 8 * 1024 * 1024 * 1024  # 8GB

        mock_disk = MagicMock()
        mock_disk.percent = 45.0
        mock_disk.used = 100 * 1024 * 1024 * 1024  # 100GB
        mock_disk.total = 256 * 1024 * 1024 * 1024  # 256GB

        with patch("psutil.cpu_percent", return_value=25.0):
            with patch("psutil.virtual_memory", return_value=mock_memory):
                with patch("psutil.disk_usage", return_value=mock_disk):
                    metrics = service.get_system_metrics()

        assert metrics.cpu_percent == 25.0
        assert metrics.memory_percent == 65.5
        assert metrics.disk_percent == 45.0

    def test_get_metrics_error(self, service):
        """获取指标失败返回零值"""
        with patch("psutil.cpu_percent", side_effect=Exception("Error")):
            metrics = service.get_system_metrics()

        assert metrics.cpu_percent == 0
        assert metrics.memory_percent == 0


# =============================================================================
# 整体状态计算测试
# =============================================================================

class TestCalculateOverallStatus:
    """整体状态计算测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(HealthMonitorService)
        svc._initialized = True
        return svc

    def test_all_healthy(self, service):
        """全部健康 = HEALTHY"""
        components = [
            ComponentHealth(name="a", status=HealthStatus.HEALTHY, last_check=datetime.now()),
            ComponentHealth(name="b", status=HealthStatus.HEALTHY, last_check=datetime.now()),
            ComponentHealth(name="c", status=HealthStatus.HEALTHY, last_check=datetime.now()),
        ]

        status = service._calculate_overall_status(components)

        assert status == HealthStatus.HEALTHY

    def test_one_unhealthy(self, service):
        """任一不健康 = UNHEALTHY"""
        components = [
            ComponentHealth(name="a", status=HealthStatus.HEALTHY, last_check=datetime.now()),
            ComponentHealth(name="b", status=HealthStatus.UNHEALTHY, last_check=datetime.now()),
            ComponentHealth(name="c", status=HealthStatus.HEALTHY, last_check=datetime.now()),
        ]

        status = service._calculate_overall_status(components)

        assert status == HealthStatus.UNHEALTHY

    def test_some_degraded(self, service):
        """部分降级 = DEGRADED"""
        components = [
            ComponentHealth(name="a", status=HealthStatus.HEALTHY, last_check=datetime.now()),
            ComponentHealth(name="b", status=HealthStatus.DEGRADED, last_check=datetime.now()),
            ComponentHealth(name="c", status=HealthStatus.HEALTHY, last_check=datetime.now()),
        ]

        status = service._calculate_overall_status(components)

        assert status == HealthStatus.DEGRADED

    def test_majority_degraded(self, service):
        """多数降级 = DEGRADED"""
        components = [
            ComponentHealth(name="a", status=HealthStatus.DEGRADED, last_check=datetime.now()),
            ComponentHealth(name="b", status=HealthStatus.DEGRADED, last_check=datetime.now()),
            ComponentHealth(name="c", status=HealthStatus.HEALTHY, last_check=datetime.now()),
        ]

        status = service._calculate_overall_status(components)

        assert status == HealthStatus.DEGRADED


# =============================================================================
# 组件健康检查测试
# =============================================================================

class TestComponentChecks:
    """组件健康检查测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(HealthMonitorService)
        svc._initialized = True
        svc._error_history = HealthMonitorService._error_history.__class__(maxlen=100)
        return svc

    @pytest.mark.asyncio
    async def test_check_database_healthy(self, service):
        """数据库健康检查 - 成功"""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.exec = MagicMock()

        with patch("sqlmodel.Session", return_value=mock_session):
            with patch("db.models.engine"):
                with patch("config.settings.settings") as mock_settings:
                    mock_settings.DATABASE_MODE = "sqlite"
                    result = await service.check_database()

        assert result.name == "database"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    @pytest.mark.asyncio
    async def test_check_database_unhealthy(self, service):
        """数据库健康检查 - 失败"""
        with patch("sqlmodel.Session", side_effect=Exception("DB Error")):
            result = await service.check_database()

        assert result.status == HealthStatus.UNHEALTHY
        assert "DB Error" in result.message

    @pytest.mark.asyncio
    async def test_check_llm_providers_configured(self, service):
        """LLM 提供商检查 - 已配置"""
        # 直接调用方法，使用实际 settings
        # 测试返回的格式正确即可
        result = await service.check_llm_providers()

        assert result.name == "llm_providers"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
        assert result.last_check is not None

    @pytest.mark.asyncio
    async def test_check_llm_providers_returns_correct_format(self, service):
        """LLM 提供商检查 - 返回格式正确"""
        result = await service.check_llm_providers()

        # 验证返回的 ComponentHealth 结构
        assert isinstance(result, ComponentHealth)
        assert result.name == "llm_providers"
        # 根据实际配置决定状态，但格式应正确
        if result.status == HealthStatus.HEALTHY:
            assert "Available:" in result.message
        else:
            assert "No LLM" in result.message

    @pytest.mark.asyncio
    async def test_check_chromadb_available(self, service):
        """ChromaDB 检查 - 可用"""
        mock_memory_service = MagicMock()
        mock_memory_service.is_available.return_value = True
        mock_memory_service.get_stats.return_value = {"total_memories": 100}

        with patch("services.memory_service.memory_service", mock_memory_service):
            result = await service.check_chromadb()

        assert result.status == HealthStatus.HEALTHY
        assert "100" in result.message

    @pytest.mark.asyncio
    async def test_check_chromadb_unavailable(self, service):
        """ChromaDB 检查 - 不可用"""
        mock_memory_service = MagicMock()
        mock_memory_service.is_available.return_value = False

        with patch("services.memory_service.memory_service", mock_memory_service):
            result = await service.check_chromadb()

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_scheduler_with_jobs(self, service):
        """调度器检查 - 有任务"""
        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = [MagicMock(), MagicMock()]

        with patch("services.scheduler.watchlist_scheduler", mock_scheduler):
            result = await service.check_scheduler()

        assert result.status == HealthStatus.HEALTHY
        assert "2" in result.message

    @pytest.mark.asyncio
    async def test_check_scheduler_no_jobs(self, service):
        """调度器检查 - 无任务"""
        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = []

        with patch("services.scheduler.watchlist_scheduler", mock_scheduler):
            result = await service.check_scheduler()

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_market_watcher_available(self, service):
        """市场监控检查 - 可用"""
        mock_watcher = MagicMock()
        mock_watcher.get_stats.return_value = {
            "akshare_available": True,
            "yfinance_available": True,
            "cached_indices": 5,
        }

        with patch("services.market_watcher.market_watcher", mock_watcher):
            result = await service.check_market_watcher()

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_market_watcher_no_providers(self, service):
        """市场监控检查 - 无数据源"""
        mock_watcher = MagicMock()
        mock_watcher.get_stats.return_value = {
            "akshare_available": False,
            "yfinance_available": False,
        }

        with patch("services.market_watcher.market_watcher", mock_watcher):
            result = await service.check_market_watcher()

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_news_aggregator_available(self, service):
        """新闻聚合检查 - 可用"""
        mock_aggregator = MagicMock()
        mock_aggregator.get_stats.return_value = {
            "feedparser_available": True,
            "finnhub_available": False,
            "cached_news": 50,
        }

        with patch("services.news_aggregator.news_aggregator", mock_aggregator):
            result = await service.check_news_aggregator()

        assert result.status == HealthStatus.HEALTHY


# =============================================================================
# 健康报告测试
# =============================================================================

class TestGetHealthReport:
    """健康报告测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(HealthMonitorService)
        svc._initialized = True
        svc._start_time = datetime.now() - timedelta(hours=1)
        svc._error_history = HealthMonitorService._error_history.__class__(maxlen=100)
        svc._component_cache = {}
        svc._last_check = None
        svc._cache_ttl = timedelta(seconds=30)
        return svc

    @pytest.mark.asyncio
    async def test_get_report_fresh(self, service):
        """获取新鲜报告"""
        mock_health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            last_check=datetime.now(),
        )

        with patch.object(service, 'check_database', return_value=mock_health):
            with patch.object(service, 'check_chromadb', return_value=mock_health):
                with patch.object(service, 'check_scheduler', return_value=mock_health):
                    with patch.object(service, 'check_market_watcher', return_value=mock_health):
                        with patch.object(service, 'check_news_aggregator', return_value=mock_health):
                            with patch.object(service, 'check_llm_providers', return_value=mock_health):
                                with patch.object(service, 'get_system_metrics', return_value=SystemMetrics(
                                    cpu_percent=10, memory_percent=50,
                                    memory_used_mb=4000, memory_total_mb=8000,
                                    disk_percent=30, disk_used_gb=50, disk_total_gb=200,
                                )):
                                    report = await service.get_health_report(force_refresh=True)

        assert isinstance(report, HealthReport)
        assert report.overall_status == HealthStatus.HEALTHY
        assert len(report.components) == 6
        assert report.uptime_seconds > 0

    @pytest.mark.asyncio
    async def test_get_report_cached(self, service):
        """使用缓存报告"""
        cached_health = ComponentHealth(
            name="cached",
            status=HealthStatus.HEALTHY,
            last_check=datetime.now(),
        )
        service._component_cache = {"cached": cached_health}
        service._last_check = datetime.now()

        with patch.object(service, 'get_system_metrics', return_value=SystemMetrics(
            cpu_percent=10, memory_percent=50,
            memory_used_mb=4000, memory_total_mb=8000,
            disk_percent=30, disk_used_gb=50, disk_total_gb=200,
        )):
            report = await service.get_health_report()

        assert len(report.components) == 1
        assert report.components[0].name == "cached"


# =============================================================================
# 运行时间测试
# =============================================================================

class TestGetUptime:
    """运行时间测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(HealthMonitorService)
        svc._initialized = True
        svc._start_time = datetime.now() - timedelta(hours=2, minutes=30)
        return svc

    def test_get_uptime(self, service):
        """获取运行时间"""
        uptime = service.get_uptime()

        assert "start_time" in uptime
        assert "uptime_seconds" in uptime
        assert "uptime_formatted" in uptime
        assert "current_time" in uptime

        # 运行时间应该大于 2 小时
        assert uptime["uptime_seconds"] > 2 * 3600


# =============================================================================
# 错误清除测试
# =============================================================================

class TestClearErrors:
    """错误清除测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(HealthMonitorService)
        svc._initialized = True
        svc._error_history = HealthMonitorService._error_history.__class__(maxlen=100)
        return svc

    def test_clear_errors(self, service):
        """清除错误历史"""
        # 添加一些错误
        service._error_history.append(ErrorRecord(
            timestamp=datetime.now(),
            component="test",
            error_type="Error",
            message="Test error",
        ))

        count = service.clear_errors()

        assert count == 1
        assert len(service._error_history) == 0


# =============================================================================
# 单例测试
# =============================================================================

class TestHealthMonitorSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert health_monitor is not None
        assert isinstance(health_monitor, HealthMonitorService)

    def test_singleton_same_instance(self):
        """多次实例化返回同一对象"""
        instance1 = HealthMonitorService()
        instance2 = HealthMonitorService()

        assert instance1 is instance2
