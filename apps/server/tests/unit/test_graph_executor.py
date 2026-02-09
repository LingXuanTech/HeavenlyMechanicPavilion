"""
测试 graph_executor 模块

测试统一的图执行器和报告收集功能
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.graph_executor import (
    execute_trading_graph,
    collect_agent_reports,
    GraphExecutionResult,
)


class TestCollectAgentReports:
    """测试报告收集函数"""

    def test_collect_basic_reports(self):
        """测试收集基本分析师报告"""
        node_data = {
            "macro_report": "宏观经济分析...",
            "market_report": "市场技术分析...",
            "news_report": "新闻舆情分析...",
        }
        agent_reports = {}

        collect_agent_reports(node_data, agent_reports)

        assert agent_reports["macro"] == "宏观经济分析..."
        assert agent_reports["market"] == "市场技术分析..."
        assert agent_reports["news"] == "新闻舆情分析..."

    def test_collect_a_stock_reports(self):
        """测试收集 A股专用报告"""
        node_data = {
            "policy_report": "政策分析...",
            "retail_sentiment_report": "散户情绪分析...",
        }
        agent_reports = {}

        collect_agent_reports(node_data, agent_reports)

        assert agent_reports["policy"] == "政策分析..."
        assert agent_reports["retail_sentiment"] == "散户情绪分析..."

    def test_collect_debate_and_risk(self):
        """测试收集辩论和风险评估结果"""
        node_data = {
            "investment_plan": "投资计划...",
            "final_trade_decision": "最终交易决策...",
            "investment_debate_state": "多空辩论状态...",
            "risk_debate_state": "风险辩论状态...",
        }
        agent_reports = {}

        collect_agent_reports(node_data, agent_reports)

        assert agent_reports["investment_plan"] == "投资计划..."
        assert agent_reports["final_trade_decision"] == "最终交易决策..."
        assert agent_reports["debate"] == "多空辩论状态..."
        assert agent_reports["risk_debate"] == "风险辩论状态..."

    def test_collect_empty_node_data(self):
        """测试空节点数据"""
        node_data = {}
        agent_reports = {}

        collect_agent_reports(node_data, agent_reports)

        assert len(agent_reports) == 0

    def test_collect_partial_reports(self):
        """测试部分报告收集"""
        node_data = {
            "market_report": "市场分析...",
            "other_field": "其他数据",  # 应该被忽略
        }
        agent_reports = {}

        collect_agent_reports(node_data, agent_reports)

        assert agent_reports["market"] == "市场分析..."
        assert "other_field" not in agent_reports
        assert len(agent_reports) == 1


class TestGraphExecutionResult:
    """测试 GraphExecutionResult 类"""

    def test_create_result(self):
        """测试创建执行结果"""
        agent_reports = {"market": "报告内容"}
        elapsed_seconds = 45.2
        final_state = {"status": "completed"}

        result = GraphExecutionResult(
            agent_reports=agent_reports,
            elapsed_seconds=elapsed_seconds,
            final_state=final_state,
        )

        assert result.agent_reports == agent_reports
        assert result.elapsed_seconds == elapsed_seconds
        assert result.final_state == final_state

    def test_create_result_without_final_state(self):
        """测试创建结果时不提供 final_state"""
        result = GraphExecutionResult(
            agent_reports={},
            elapsed_seconds=10.0,
        )

        assert result.final_state == {}


@pytest.mark.asyncio
class TestExecuteTradingGraph:
    """测试图执行函数"""

    @patch("services.graph_executor.TradingAgentsGraph")
    @patch("services.graph_executor.MarketRouter")
    async def test_execute_l1_analysis(self, mock_router, mock_graph_class):
        """测试 L1 快速分析"""
        # Mock MarketRouter
        mock_router.get_market.return_value = "US"

        # Mock TradingAgentsGraph
        mock_graph = Mock()
        mock_propagator = Mock()
        mock_propagator.create_initial_state.return_value = {"symbol": "AAPL"}
        mock_propagator.get_graph_args.return_value = {}
        mock_graph.propagator = mock_propagator

        # Mock graph.stream 返回分析结果
        mock_graph.graph.stream.return_value = [
            {"Market Analyst": {"market_report": "市场分析报告"}},
            {"News Analyst": {"news_report": "新闻分析报告"}},
        ]

        mock_graph_class.return_value = mock_graph

        # 执行 L1 分析
        result = await execute_trading_graph(
            symbol="AAPL",
            analysis_level="L1",
            use_planner=False,
        )

        # 验证结果
        assert isinstance(result, GraphExecutionResult)
        assert "market" in result.agent_reports
        assert "news" in result.agent_reports
        assert result.elapsed_seconds > 0

        # 验证 L1 配置
        mock_graph_class.assert_called_once()
        call_kwargs = mock_graph_class.call_args[1]
        assert call_kwargs["config"]["analysis_level"] == "L1"
        assert call_kwargs["config"]["enable_debate"] is False

    @patch("services.graph_executor.TradingAgentsGraph")
    @patch("services.graph_executor.MarketRouter")
    async def test_execute_with_callback(self, mock_router, mock_graph_class):
        """测试带回调的执行"""
        mock_router.get_market.return_value = "US"

        mock_graph = Mock()
        mock_propagator = Mock()
        mock_propagator.create_initial_state.return_value = {"symbol": "AAPL"}
        mock_propagator.get_graph_args.return_value = {}
        mock_graph.propagator = mock_propagator
        mock_graph.graph.stream.return_value = [
            {"Market Analyst": {"market_report": "报告"}},
        ]
        mock_graph_class.return_value = mock_graph

        # 创建回调 mock
        callback = AsyncMock()

        # 执行
        await execute_trading_graph(
            symbol="AAPL",
            on_node_complete=callback,
        )

        # 验证回调被调用
        callback.assert_called_once_with("Market Analyst", {"market_report": "报告"})

    @patch("services.graph_executor.TradingAgentsGraph")
    @patch("services.graph_executor.MarketRouter")
    async def test_execute_with_historical_reflection(self, mock_router, mock_graph_class):
        """测试带历史反思的执行"""
        mock_router.get_market.return_value = "US"

        mock_graph = Mock()
        mock_propagator = Mock()
        mock_propagator.create_initial_state.return_value = {"symbol": "AAPL"}
        mock_propagator.get_graph_args.return_value = {}
        mock_graph.propagator = mock_propagator
        mock_graph.graph.stream.return_value = []
        mock_graph_class.return_value = mock_graph

        reflection = "历史反思信息..."

        # 执行
        await execute_trading_graph(
            symbol="AAPL",
            historical_reflection=reflection,
        )

        # 验证 historical_reflection 被传递
        mock_propagator.create_initial_state.assert_called_once()
        call_kwargs = mock_propagator.create_initial_state.call_args[1]
        assert call_kwargs["historical_reflection"] == reflection

    @patch("services.graph_executor.TradingAgentsGraph")
    @patch("services.graph_executor.MarketRouter")
    async def test_execute_with_custom_date(self, mock_router, mock_graph_class):
        """测试自定义日期"""
        mock_router.get_market.return_value = "US"

        mock_graph = Mock()
        mock_propagator = Mock()
        mock_propagator.create_initial_state.return_value = {"symbol": "AAPL"}
        mock_propagator.get_graph_args.return_value = {}
        mock_graph.propagator = mock_propagator
        mock_graph.graph.stream.return_value = []
        mock_graph_class.return_value = mock_graph

        custom_date = "2024-01-15"

        # 执行
        await execute_trading_graph(
            symbol="AAPL",
            trade_date=custom_date,
        )

        # 验证日期被传递
        mock_propagator.create_initial_state.assert_called_once()
        call_args = mock_propagator.create_initial_state.call_args[0]
        assert call_args[1] == custom_date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
