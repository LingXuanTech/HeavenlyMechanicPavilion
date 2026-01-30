"""Agent 弹性执行模块单元测试

测试超时处理、降级机制和执行监控。
"""

import pytest
import time
from unittest.mock import MagicMock, patch


class TestResilientNodeWrapper:
    """弹性节点包装器测试"""

    def test_successful_execution(self):
        """测试成功执行"""
        from tradingagents.graph.resilience import ResilientNodeWrapper

        def mock_node(state):
            return {"messages": [], "market_report": "Test report"}

        wrapper = ResilientNodeWrapper(
            node_func=mock_node,
            node_name="Test Node",
            timeout_seconds=5,
        )

        result = wrapper({"messages": []})

        assert "market_report" in result
        assert result["market_report"] == "Test report"

    def test_timeout_degradation(self):
        """测试超时降级"""
        from tradingagents.graph.resilience import ResilientNodeWrapper

        def slow_node(state):
            time.sleep(10)
            return {"market_report": "Should not reach"}

        wrapper = ResilientNodeWrapper(
            node_func=slow_node,
            node_name="Market Analyst",
            timeout_seconds=1,
            max_retries=0,
            fallback_result={"market_report": "Degraded report"},
        )

        result = wrapper({"messages": []})

        # 应该返回降级结果
        assert "market_report" in result
        assert "Degraded" in result["market_report"] or "unavailable" in result["market_report"]

    def test_error_degradation(self):
        """测试异常降级"""
        from tradingagents.graph.resilience import ResilientNodeWrapper

        def error_node(state):
            raise ValueError("Simulated error")

        wrapper = ResilientNodeWrapper(
            node_func=error_node,
            node_name="News Analyst",
            timeout_seconds=5,
            max_retries=0,
            fallback_result={"news_report": "Fallback report"},
        )

        result = wrapper({"messages": []})

        # 应该返回降级结果而不是抛出异常
        assert "news_report" in result
        assert "unavailable" in result.get("news_report", "").lower() or "Fallback" in result.get("news_report", "")

    def test_retry_success(self):
        """测试重试后成功"""
        from tradingagents.graph.resilience import ResilientNodeWrapper

        call_count = [0]

        def flaky_node(state):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("Temporary error")
            return {"market_report": "Success after retry"}

        wrapper = ResilientNodeWrapper(
            node_func=flaky_node,
            node_name="Market Analyst",
            timeout_seconds=5,
            max_retries=2,
            retry_delay=0.1,
        )

        result = wrapper({"messages": []})

        assert call_count[0] == 2
        assert result.get("market_report") == "Success after retry"


class TestAnalystNodeFactory:
    """分析师节点工厂测试"""

    def test_wrap_analyst_node(self):
        """测试包装分析师节点"""
        from tradingagents.graph.resilience import AnalystNodeFactory

        def mock_analyst(state):
            return {"market_report": "Test analysis"}

        wrapped = AnalystNodeFactory.wrap_analyst_node(mock_analyst, "market")

        assert wrapped.node_name == "Market Analyst"
        assert wrapped.timeout_seconds == 45  # Default for market

    def test_custom_timeout(self):
        """测试自定义超时"""
        from tradingagents.graph.resilience import AnalystNodeFactory

        def mock_analyst(state):
            return {}

        wrapped = AnalystNodeFactory.wrap_analyst_node(
            mock_analyst, "policy", custom_timeout=30
        )

        assert wrapped.timeout_seconds == 30

    def test_fallback_content(self):
        """测试降级内容设置正确"""
        from tradingagents.graph.resilience import AnalystNodeFactory

        def error_analyst(state):
            raise ValueError("Error")

        wrapped = AnalystNodeFactory.wrap_analyst_node(error_analyst, "news")
        result = wrapped({"messages": []})

        # 应该有 news_report 字段的降级内容
        assert "news_report" in result
        assert "unavailable" in result["news_report"].lower()


class TestExecutionMonitor:
    """执行监控器测试"""

    def test_record_execution(self):
        """测试记录执行"""
        from tradingagents.graph.resilience import ExecutionMonitor

        monitor = ExecutionMonitor()
        monitor.reset()

        monitor.record_execution("Market Analyst", 1500, success=True)
        monitor.record_execution("News Analyst", 2000, success=False, error="Timeout")

        summary = monitor.get_summary()

        assert summary["node_metrics"]["Market Analyst"]["successful"] == 1
        assert summary["node_metrics"]["News Analyst"]["failed"] == 1
        assert len(summary["recent_failures"]) == 1

    def test_singleton(self):
        """测试单例模式"""
        from tradingagents.graph.resilience import ExecutionMonitor

        monitor1 = ExecutionMonitor()
        monitor2 = ExecutionMonitor()

        assert monitor1 is monitor2


class TestNodeTimeout:
    """节点超时配置测试"""

    def test_timeout_config(self):
        """测试各分析师的默认超时配置"""
        from tradingagents.graph.resilience import AnalystNodeFactory

        # 验证默认超时配置
        assert AnalystNodeFactory.TIMEOUT_CONFIG["market"] == 45
        assert AnalystNodeFactory.TIMEOUT_CONFIG["news"] == 60
        assert AnalystNodeFactory.TIMEOUT_CONFIG["fundamentals"] == 60
        assert AnalystNodeFactory.TIMEOUT_CONFIG["scout"] == 30

    def test_report_field_mapping(self):
        """测试报告字段映射正确"""
        from tradingagents.graph.resilience import ResilientNodeWrapper

        wrapper = ResilientNodeWrapper(
            node_func=lambda s: {},
            node_name="Policy Analyst",
            timeout_seconds=30,
        )

        field = wrapper._get_report_field_for_node()
        assert field == "policy_report"


class TestWithTimeoutDecorator:
    """装饰器测试"""

    def test_decorator_success(self):
        """测试装饰器正常执行"""
        from tradingagents.graph.resilience import with_timeout

        @with_timeout(timeout_seconds=5)
        def my_node(state):
            return {"result": "success"}

        result = my_node({"messages": []})
        assert result["result"] == "success"

    def test_decorator_timeout(self):
        """测试装饰器超时处理"""
        from tradingagents.graph.resilience import with_timeout

        @with_timeout(timeout_seconds=1, max_retries=0, fallback_result={"result": "fallback"})
        def slow_node(state):
            time.sleep(5)
            return {"result": "should not reach"}

        result = slow_node({"messages": []})

        # 应该返回降级结果
        assert "result" in result
