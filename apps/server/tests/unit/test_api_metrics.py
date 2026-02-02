"""
APIMetricsService 单元测试

覆盖:
1. RequestMetrics 数据类
2. PathMetrics 数据类
3. 路径规范化
4. 请求记录
5. 指标获取
6. 慢请求查询
7. 重置功能
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from services.api_metrics import (
    APIMetricsService,
    RequestMetrics,
    PathMetrics,
    api_metrics,
)


# =============================================================================
# RequestMetrics 测试
# =============================================================================

class TestRequestMetrics:
    """RequestMetrics 数据类测试"""

    def test_request_metrics_creation(self):
        """创建 RequestMetrics"""
        now = datetime.now()
        metrics = RequestMetrics(
            method="GET",
            path="/api/health",
            status_code=200,
            duration_ms=50.5,
            timestamp=now,
        )

        assert metrics.method == "GET"
        assert metrics.path == "/api/health"
        assert metrics.status_code == 200
        assert metrics.duration_ms == 50.5
        assert metrics.timestamp == now

    def test_request_metrics_default_timestamp(self):
        """RequestMetrics 默认时间戳"""
        before = datetime.now()
        metrics = RequestMetrics(
            method="POST",
            path="/api/analyze",
            status_code=202,
            duration_ms=100.0,
        )
        after = datetime.now()

        assert before <= metrics.timestamp <= after


# =============================================================================
# PathMetrics 测试
# =============================================================================

class TestPathMetrics:
    """PathMetrics 数据类测试"""

    def test_path_metrics_defaults(self):
        """PathMetrics 默认值"""
        metrics = PathMetrics()

        assert metrics.total_requests == 0
        assert metrics.total_errors == 0
        assert metrics.total_client_errors == 0
        assert metrics.total_success == 0
        assert metrics.total_duration_ms == 0.0
        assert metrics.min_duration_ms == float('inf')
        assert metrics.max_duration_ms == 0.0

    def test_add_success_request(self):
        """添加成功请求 (2xx)"""
        metrics = PathMetrics()
        metrics.add_request(200, 50.0)

        assert metrics.total_requests == 1
        assert metrics.total_success == 1
        assert metrics.total_client_errors == 0
        assert metrics.total_errors == 0
        assert metrics.total_duration_ms == 50.0
        assert metrics.min_duration_ms == 50.0
        assert metrics.max_duration_ms == 50.0

    def test_add_client_error_request(self):
        """添加客户端错误请求 (4xx)"""
        metrics = PathMetrics()
        metrics.add_request(404, 30.0)

        assert metrics.total_requests == 1
        assert metrics.total_success == 0
        assert metrics.total_client_errors == 1
        assert metrics.total_errors == 0

    def test_add_server_error_request(self):
        """添加服务器错误请求 (5xx)"""
        metrics = PathMetrics()
        metrics.add_request(500, 100.0)

        assert metrics.total_requests == 1
        assert metrics.total_success == 0
        assert metrics.total_client_errors == 0
        assert metrics.total_errors == 1

    def test_multiple_requests(self):
        """添加多个请求"""
        metrics = PathMetrics()
        metrics.add_request(200, 50.0)
        metrics.add_request(200, 30.0)
        metrics.add_request(500, 100.0)
        metrics.add_request(404, 20.0)

        assert metrics.total_requests == 4
        assert metrics.total_success == 2
        assert metrics.total_client_errors == 1
        assert metrics.total_errors == 1
        assert metrics.total_duration_ms == 200.0
        assert metrics.min_duration_ms == 20.0
        assert metrics.max_duration_ms == 100.0

    def test_avg_duration_ms(self):
        """平均延迟计算"""
        metrics = PathMetrics()
        metrics.add_request(200, 50.0)
        metrics.add_request(200, 100.0)

        assert metrics.avg_duration_ms == 75.0

    def test_avg_duration_ms_empty(self):
        """空请求时平均延迟为 0"""
        metrics = PathMetrics()
        assert metrics.avg_duration_ms == 0.0

    def test_error_rate(self):
        """错误率计算"""
        metrics = PathMetrics()
        metrics.add_request(200, 50.0)
        metrics.add_request(500, 100.0)

        assert metrics.error_rate == 50.0

    def test_error_rate_empty(self):
        """空请求时错误率为 0"""
        metrics = PathMetrics()
        assert metrics.error_rate == 0.0

    def test_success_rate(self):
        """成功率计算"""
        metrics = PathMetrics()
        metrics.add_request(200, 50.0)
        metrics.add_request(200, 30.0)
        metrics.add_request(500, 100.0)
        metrics.add_request(404, 20.0)

        assert metrics.success_rate == 50.0

    def test_success_rate_empty(self):
        """空请求时成功率为 0"""
        metrics = PathMetrics()
        assert metrics.success_rate == 0.0


# =============================================================================
# 路径规范化测试
# =============================================================================

class TestNormalizePath:
    """路径规范化测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return APIMetricsService()

    def test_remove_query_string(self, service):
        """移除查询字符串"""
        path = "/api/health?check=true"
        result = service._normalize_path(path)

        assert result == "/api/health"

    def test_normalize_task_id(self, service):
        """规范化任务 ID"""
        path = "/api/analyze/stream/task_abc_1234"
        result = service._normalize_path(path)

        assert "{task_id}" in result

    def test_normalize_uuid(self, service):
        """规范化 UUID"""
        path = "/api/user/123e4567-e89b-12d3-a456-426614174000"
        result = service._normalize_path(path)

        assert "{uuid}" in result

    def test_normalize_numeric_id(self, service):
        """规范化数字 ID"""
        path = "/api/watchlist/12345"
        result = service._normalize_path(path)

        assert "{id}" in result

    def test_normalize_stock_symbol_uppercase(self, service):
        """纯字母代码不被规范化（无数字不匹配）"""
        path = "/api/stock/AAPL"
        result = service._normalize_path(path)

        # AAPL 纯字母无数字，不会被替换为 {symbol}
        assert result == "/api/stock/AAPL"

    def test_normalize_stock_symbol_with_dot(self, service):
        """规范化股票代码 (带点号)"""
        path = "/api/stock/600519.SH"
        result = service._normalize_path(path)

        assert "{symbol}" in result

    def test_preserve_regular_path(self, service):
        """保留普通路径"""
        path = "/api/health"
        result = service._normalize_path(path)

        assert result == "/api/health"


# =============================================================================
# 请求记录测试
# =============================================================================

class TestRecordRequest:
    """请求记录测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return APIMetricsService(history_limit=10, window_minutes=5)

    def test_record_single_request(self, service):
        """记录单个请求"""
        service.record_request("GET", "/api/health", 200, 50.0)

        metrics = service.get_metrics()
        assert metrics["global"]["total_requests"] == 1
        assert metrics["global"]["total_errors"] == 0

    def test_record_multiple_requests(self, service):
        """记录多个请求"""
        service.record_request("GET", "/api/health", 200, 50.0)
        service.record_request("POST", "/api/analyze", 202, 100.0)
        service.record_request("GET", "/api/health", 500, 200.0)

        metrics = service.get_metrics()
        assert metrics["global"]["total_requests"] == 3
        assert metrics["global"]["total_errors"] == 1

    def test_record_request_path_aggregation(self, service):
        """请求按路径聚合"""
        service.record_request("GET", "/api/health", 200, 50.0)
        service.record_request("GET", "/api/health", 200, 30.0)
        service.record_request("GET", "/api/health", 200, 40.0)

        metrics = service.get_metrics()
        path_stats = metrics["by_path"]["GET /api/health"]

        assert path_stats["requests"] == 3
        assert path_stats["avg_duration_ms"] == 40.0

    def test_history_limit(self, service):
        """历史记录限制"""
        for i in range(15):
            service.record_request("GET", "/api/health", 200, 10.0)

        # history_limit = 10，所以最多保留 10 条
        assert len(service._recent_requests) == 10


# =============================================================================
# 指标获取测试
# =============================================================================

class TestGetMetrics:
    """指标获取测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return APIMetricsService(window_minutes=5)

    def test_get_metrics_empty(self, service):
        """空指标"""
        metrics = service.get_metrics()

        assert metrics["global"]["total_requests"] == 0
        assert metrics["global"]["total_errors"] == 0
        assert metrics["global"]["avg_duration_ms"] == 0
        assert metrics["global"]["error_rate_pct"] == 0
        assert metrics["window"]["requests"] == 0
        assert len(metrics["by_path"]) == 0

    def test_get_metrics_with_data(self, service):
        """有数据的指标"""
        service.record_request("GET", "/api/health", 200, 50.0)
        service.record_request("GET", "/api/analyze", 500, 100.0)

        metrics = service.get_metrics()

        assert metrics["global"]["total_requests"] == 2
        assert metrics["global"]["total_errors"] == 1
        assert metrics["global"]["error_rate_pct"] == 50.0

    def test_get_metrics_uptime(self, service):
        """运行时间"""
        metrics = service.get_metrics()

        assert "uptime_seconds" in metrics
        assert metrics["uptime_seconds"] >= 0

    def test_get_metrics_window(self, service):
        """滑动窗口指标"""
        service.record_request("GET", "/api/health", 200, 50.0)

        metrics = service.get_metrics()

        assert metrics["window"]["window_minutes"] == 5
        assert metrics["window"]["requests"] == 1

    def test_get_metrics_path_stats(self, service):
        """路径统计"""
        service.record_request("GET", "/api/health", 200, 50.0)
        service.record_request("GET", "/api/health", 200, 100.0)

        metrics = service.get_metrics()
        path_stats = metrics["by_path"]["GET /api/health"]

        assert path_stats["requests"] == 2
        assert path_stats["success"] == 2
        assert path_stats["success_rate_pct"] == 100.0
        assert path_stats["avg_duration_ms"] == 75.0
        assert path_stats["min_duration_ms"] == 50.0
        assert path_stats["max_duration_ms"] == 100.0


# =============================================================================
# 滑动窗口测试
# =============================================================================

class TestWindowCleanup:
    """滑动窗口清理测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例（1分钟窗口）"""
        return APIMetricsService(window_minutes=1)

    def test_cleanup_old_requests(self, service):
        """清理过期请求"""
        # 手动添加过期请求
        old_request = RequestMetrics(
            method="GET",
            path="/api/old",
            status_code=200,
            duration_ms=50.0,
            timestamp=datetime.now() - timedelta(minutes=5),
        )
        service._window_requests.append(old_request)

        # 添加新请求触发清理
        service.record_request("GET", "/api/new", 200, 50.0)

        # 过期请求应该被清理
        assert len(service._window_requests) == 1
        assert service._window_requests[0].path == "/api/new"


# =============================================================================
# 慢请求查询测试
# =============================================================================

class TestGetSlowRequests:
    """慢请求查询测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return APIMetricsService()

    def test_get_slow_requests_empty(self, service):
        """无慢请求"""
        service.record_request("GET", "/api/health", 200, 50.0)

        slow = service.get_slow_requests(threshold_ms=1000.0)
        assert slow == []

    def test_get_slow_requests_found(self, service):
        """找到慢请求"""
        service.record_request("GET", "/api/fast", 200, 50.0)
        service.record_request("GET", "/api/slow", 200, 1500.0)
        service.record_request("GET", "/api/very_slow", 200, 3000.0)

        slow = service.get_slow_requests(threshold_ms=1000.0)

        assert len(slow) == 2
        # 按延迟降序排序
        assert slow[0]["duration_ms"] == 3000.0
        assert slow[1]["duration_ms"] == 1500.0

    def test_get_slow_requests_limit(self, service):
        """限制返回数量"""
        for i in range(20):
            service.record_request("GET", f"/api/slow/{i}", 200, 2000.0 + i)

        slow = service.get_slow_requests(threshold_ms=1000.0, limit=5)

        assert len(slow) == 5

    def test_get_slow_requests_custom_threshold(self, service):
        """自定义阈值"""
        service.record_request("GET", "/api/medium", 200, 500.0)
        service.record_request("GET", "/api/slow", 200, 1000.0)

        slow = service.get_slow_requests(threshold_ms=400.0)

        assert len(slow) == 2


# =============================================================================
# 重置测试
# =============================================================================

class TestReset:
    """重置功能测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return APIMetricsService()

    def test_reset_clears_all(self, service):
        """重置清空所有数据"""
        service.record_request("GET", "/api/health", 200, 50.0)
        service.record_request("POST", "/api/analyze", 500, 100.0)

        service.reset()

        metrics = service.get_metrics()
        assert metrics["global"]["total_requests"] == 0
        assert len(metrics["by_path"]) == 0

    def test_reset_updates_start_time(self, service):
        """重置更新启动时间"""
        old_start = service._start_time

        import time
        time.sleep(0.1)

        service.reset()

        assert service._start_time > old_start


# =============================================================================
# 线程安全测试
# =============================================================================

class TestThreadSafety:
    """线程安全测试"""

    def test_concurrent_record_requests(self):
        """并发记录请求"""
        import threading

        service = APIMetricsService()
        threads = []

        def record_requests():
            for _ in range(100):
                service.record_request("GET", "/api/health", 200, 50.0)

        for _ in range(10):
            t = threading.Thread(target=record_requests)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        metrics = service.get_metrics()
        assert metrics["global"]["total_requests"] == 1000


# =============================================================================
# 单例测试
# =============================================================================

class TestAPIMetricsSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert api_metrics is not None
        assert isinstance(api_metrics, APIMetricsService)
