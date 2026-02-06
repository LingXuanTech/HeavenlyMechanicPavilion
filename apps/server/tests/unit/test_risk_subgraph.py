import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

from tradingagents.graph.subgraphs.risk_subgraph import RiskSubGraph

@pytest.fixture
def mock_llms():
    quick_llm = MagicMock()
    quick_llm.invoke.return_value = AIMessage(content="Mocked risk analyst response")
    
    deep_llm = MagicMock()
    deep_llm.invoke.return_value = AIMessage(content="Mocked risk judge decision")
    
    return quick_llm, deep_llm

@pytest.fixture
def risk_subgraph(mock_llms):
    quick_llm, deep_llm = mock_llms
    return RiskSubGraph(
        quick_thinking_llm=quick_llm,
        deep_thinking_llm=deep_llm,
        risk_manager_memory=MagicMock(),
        max_risk_discuss_rounds=1
    )

def test_risk_subgraph_initialization(risk_subgraph):
    """测试 RiskSubGraph 初始化"""
    assert risk_subgraph.max_risk_discuss_rounds == 1
    assert risk_subgraph.quick_thinking_llm is not None

def test_risk_subgraph_compile(risk_subgraph):
    """测试风险子图编译"""
    graph = risk_subgraph.compile()
    assert graph is not None
    nodes = graph.nodes
    assert "Risky" in nodes
    assert "Safe" in nodes
    assert "Neutral" in nodes
    assert "Judge" in nodes

def test_should_continue_risk_logic(risk_subgraph):
    """测试风险讨论轮转逻辑"""
    # 1. 初始状态
    state = {"risk_debate_state": {"count": 0, "latest_speaker": ""}}
    assert risk_subgraph._should_continue_risk(state) == "Risky"
    
    # 2. Risky 刚说完，应该去 Safe
    state = {"risk_debate_state": {"count": 1, "latest_speaker": "Risky Analyst"}}
    assert risk_subgraph._should_continue_risk(state) == "Safe"
    
    # 3. Safe 刚说完，应该去 Neutral
    state = {"risk_debate_state": {"count": 2, "latest_speaker": "Safe Analyst"}}
    assert risk_subgraph._should_continue_risk(state) == "Neutral"
    
    # 4. Neutral 刚说完，应该去 Risky (如果还没到上限)
    state = {"risk_debate_state": {"count": 3, "latest_speaker": "Neutral Analyst"}}
    # 注意：max_rounds=1, 3*1=3，所以这里应该去 Judge
    assert risk_subgraph._should_continue_risk(state) == "Judge"

def test_risk_subgraph_execution(risk_subgraph):
    """测试风险子图执行流程"""
    with patch("tradingagents.agents.create_risky_debator") as mock_risky, \
         patch("tradingagents.agents.create_safe_debator") as mock_safe, \
         patch("tradingagents.agents.create_neutral_debator") as mock_neutral, \
         patch("tradingagents.agents.create_risk_manager") as mock_mgr:
        
        def risky_node(state):
            count = state.get("risk_debate_state", {}).get("count", 0)
            return {"risk_debate_state": {"count": count + 1, "latest_speaker": "Risky Analyst"}}
        
        def safe_node(state):
            count = state.get("risk_debate_state", {}).get("count", 0)
            return {"risk_debate_state": {"count": count + 1, "latest_speaker": "Safe Analyst"}}
            
        def neutral_node(state):
            count = state.get("risk_debate_state", {}).get("count", 0)
            return {"risk_debate_state": {"count": count + 1, "latest_speaker": "Neutral Analyst"}}
            
        def judge_node(state):
            return {"final_trade_decision": "Proceed with caution"}
            
        mock_risky.return_value = risky_node
        mock_safe.return_value = safe_node
        mock_neutral.return_value = neutral_node
        mock_mgr.return_value = judge_node
        
        graph = risk_subgraph.compile()
        
        initial_state = {
            "risk_debate_state": {"count": 0, "latest_speaker": ""},
            "messages": []
        }
        
        result = graph.invoke(initial_state)
        
        assert result["final_trade_decision"] == "Proceed with caution"
        assert result["risk_debate_state"]["count"] >= 3
