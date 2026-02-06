import pytest
from unittest.mock import MagicMock, patch
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

@pytest.fixture
def mock_ai_config_service():
    with patch("services.ai_config_service.ai_config_service") as mock_service:
        mock_llm = MagicMock(spec=ChatOpenAI)
        # 确保 invoke 返回的是 AIMessage 而不是 MagicMock
        mock_llm.invoke.return_value = AIMessage(content="Mocked response")
        # 模拟 bind_tools 行为
        mock_llm.bind_tools.return_value = mock_llm
        mock_service.get_llm.return_value = mock_llm
        yield mock_service

@pytest.fixture
def base_config():
    config = DEFAULT_CONFIG.copy()
    config["project_dir"] = "/tmp/tradingagents_test"
    return config

def test_subgraph_vs_maingraph_consistency(mock_ai_config_service, base_config):
    """对比测试：验证 SubGraph 模式与传统单图模式在相同输入下的输出一致性"""
    
    # 准备输入
    symbol = "AAPL"
    trade_date = "2026-02-06"
    
    # 定义统一的模拟行为
    def market_node(state):
        return {"market_report": "Market is good"}
    
    def bull_node(state):
        return {"investment_debate_state": {"count": 1, "current_response": "Bull: Buy", "history": "Bull: Buy"}}
        
    def bear_node(state):
        return {"investment_debate_state": {"count": 2, "current_response": "Bear: Sell", "history": "Bull: Buy\nBear: Sell"}}
        
    def mgr_node(state):
        return {"investment_plan": "Plan A"}
        
    def risky_node(state):
        return {"risk_debate_state": {"count": 1, "latest_speaker": "Risky", "history": "Risky: High risk"}}
        
    def safe_node(state):
        return {"risk_debate_state": {"count": 2, "latest_speaker": "Safe", "history": "Risky: High risk\nSafe: Low risk"}}
        
    def neutral_node(state):
        return {"risk_debate_state": {"count": 3, "latest_speaker": "Neutral", "history": "Risky: High risk\nSafe: Low risk\nNeutral: Mid risk"}}
        
    def risk_mgr_node(state):
        return {"final_trade_decision": "Decision X"}

    def generic_node(state):
        return {}

    from contextlib import ExitStack
    with ExitStack() as stack:
        # 1. Patch 所有可能被调用的 Agent 创建函数
        stack.enter_context(patch("tradingagents.agents.create_market_analyst", return_value=market_node))
        stack.enter_context(patch("tradingagents.agents.create_bull_researcher", return_value=bull_node))
        stack.enter_context(patch("tradingagents.agents.create_bear_researcher", return_value=bear_node))
        stack.enter_context(patch("tradingagents.agents.create_research_manager", return_value=mgr_node))
        stack.enter_context(patch("tradingagents.agents.create_risky_debator", return_value=risky_node))
        stack.enter_context(patch("tradingagents.agents.create_safe_debator", return_value=safe_node))
        stack.enter_context(patch("tradingagents.agents.create_neutral_debator", return_value=neutral_node))
        stack.enter_context(patch("tradingagents.agents.create_risk_manager", return_value=risk_mgr_node))
        stack.enter_context(patch("tradingagents.agents.create_msg_delete", return_value=generic_node))
        stack.enter_context(patch("tradingagents.agents.create_trader", return_value=generic_node))
        
        stack.enter_context(patch("tradingagents.agents.analysts.portfolio_agent.create_portfolio_agent", return_value=generic_node))
        stack.enter_context(patch("tradingagents.agents.analysts.macro_analyst.create_macro_analyst", return_value=generic_node))
        stack.enter_context(patch("tradingagents.agents.analysts.planner_agent.create_planner_agent", return_value=generic_node))

        # Mock 条件逻辑，避免 tool_calls AttributeError
        stack.enter_context(patch("tradingagents.graph.conditional_logic.ConditionalLogic.should_continue_market", return_value="Msg Clear Market"))
        
        # Mock FinancialSituationMemory 避免 ChromaDB 冲突
        stack.enter_context(patch("tradingagents.graph.trading_graph.FinancialSituationMemory"))
        
        # Mock _log_state 避免文件写入
        stack.enter_context(patch("tradingagents.graph.trading_graph.TradingAgentsGraph._log_state"))

        # 2. 初始化传统单图模式
        config_main = base_config.copy()
        config_main["use_subgraphs"] = False
        graph_main = TradingAgentsGraph(
            selected_analysts=["market"],
            config=config_main,
            market="US"
        )
        
        # 3. 初始化 SubGraph 模式
        config_sub = base_config.copy()
        config_sub["use_subgraphs"] = True
        graph_sub = TradingAgentsGraph(
            selected_analysts=["market"],
            config=config_sub,
            market="US"
        )
        
        # 4. 准备初始状态（使用 AIMessage 避免 tool_calls 属性错误）
        initial_state = {
            "messages": [AIMessage(content="Start")],
            "company_name": symbol,
            "company_of_interest": symbol,
            "trade_date": trade_date,
            "market_report": "",
            "fundamentals_report": "",
            "news_report": "",
            "sentiment_report": "",
            "macro_report": "",
            "investment_debate_state": {
                "bull_history": "",
                "bear_history": "",
                "history": "",
                "current_response": "",
                "judge_decision": "",
                "count": 0
            },
            "risk_debate_state": {
                "risky_history": "",
                "safe_history": "",
                "neutral_history": "",
                "history": "",
                "latest_speaker": "",
                "current_risky_response": "",
                "current_safe_response": "",
                "current_neutral_response": "",
                "judge_decision": "",
                "count": 0
            }
        }
        
        # 5. 执行并对比
        # 注意：由于 mock 了所有节点，输出应该完全一致
        res_main = graph_main.graph.invoke(initial_state)
        res_sub = graph_sub.graph.invoke(initial_state)
        
        assert res_main["investment_plan"] == res_sub["investment_plan"]
        assert res_main["final_trade_decision"] == res_sub["final_trade_decision"]
        assert "market_report" in res_main
        assert "market_report" in res_sub
