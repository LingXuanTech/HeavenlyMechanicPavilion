import pytest
from unittest.mock import patch, MagicMock
from services.data_router import MarketRouter, _record_provider_success, _record_provider_failure
from services.health_monitor import HealthMonitorService

class TestDataRouterHealth:
    """测试数据路由器的健康监控功能"""

    @pytest.fixture
    def router(self):
        # 重置单例状态
        MarketRouter._instance = None
        return MarketRouter()

    def test_provider_stats_tracking(self, router):
        """测试提供商统计信息跟踪"""
        # 模拟成功记录
        _record_provider_success("akshare", 0.5)
        status = router.get_provider_status()
        
        ak_status = status["akshare"]
        assert ak_status["total_requests"] >= 1
        assert ak_status["successful_requests"] >= 1
        assert ak_status["avg_latency_ms"] > 0

        # 模拟失败记录
        _record_provider_failure("akshare", Exception("Timeout Error"), 0.1)
        status = router.get_provider_status()
        
        ak_status = status["akshare"]
        assert ak_status["failed_requests"] >= 1
        assert ak_status["failure_count"] >= 1
        assert ak_status["last_error"] == "Timeout Error"

    def test_circuit_breaker_reset(self, router):
        """测试熔断重置逻辑"""
        # 模拟多次失败触发熔断 (假设阈值为 5)
        for _ in range(5):
            _record_provider_failure("yfinance", Exception("Error"), 0.0)
        
        status = router.get_provider_status()
        assert status["yfinance"]["available"] is False

        # 重置熔断
        router.reset_provider("yfinance")
        status = router.get_provider_status()
        assert status["yfinance"]["available"] is True
        assert status["yfinance"]["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_health_report_integration(self, router):
        """测试健康报告集成"""
        monitor = HealthMonitorService()
        
        # 记录一些数据
        _record_provider_success("alpha_vantage", 0.2)
        
        report = await monitor.get_health_report()
        # report 是 Pydantic 模型，使用 .dict() 或 .data_providers 访问
        report_dict = report.dict()
        assert "data_providers" in report_dict
        assert "alpha_vantage" in report_dict["data_providers"]
        assert report_dict["data_providers"]["alpha_vantage"]["successful_requests"] >= 1
