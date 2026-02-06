import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage

from tradingagents.graph.subgraphs.debate_subgraph import DebateSubGraph

@pytest.fixture
def mock_llms():
    quick_llm = MagicMock()
    quick_llm.invoke.return_value = AIMessage(content="Mocked researcher response")
    
    deep_llm = MagicMock()
    deep_llm.invoke.return_value = AIMessage(content="Mocked manager decision")
    
    return quick_llm, deep_llm

@pytest.fixture
def debate_subgraph(mock_llms):
    quick_llm, deep_llm = mock_llms
    return DebateSubGraph(
        quick_thinking_llm=quick_llm,
        deep_thinking_llm=deep_llm,
        bull_memory=MagicMock(),
        bear_memory=MagicMock(),
        invest_judge_memory=MagicMock(),
        max_debate_rounds=1
    )

def test_debate_subgraph_initialization(debate_subgraph):
    """测试 DebateSubGraph 初始化"""
    assert debate_subgraph.max_debate_rounds == 1
    assert debate_subgraph.quick_thinking_llm is not None

def test_debate_subgraph_compile(debate_subgraph):
    """测试辩论子图编译"""
    graph = debate_subgraph.compile()
    assert graph is not None
    nodes = graph.nodes
    assert "Bull" in nodes
    assert "Bear" in nodes
    assert "Manager" in nodes

def test_should_continue_debate_logic(debate_subgraph):
    """测试辩论轮转逻辑"""
    # 1. 初始状态，应该去 Bull
    state = {"investment_debate_state": {"count": 0, "current_response": ""}}
    assert debate_subgraph._should_continue_debate(state) == "Bull"
    
    # 2. Bull 刚说完，应该去 Bear
    state = {"investment_debate_state": {"count": 1, "current_response": "Bull: I think..."}}
    assert debate_subgraph._should_continue_debate(state) == "Bear"
    
    # 3. 达到上限 (max_rounds=1, 2*1=2)，应该去 Manager
    state = {"investment_debate_state": {"count": 2, "current_response": "Bear: I disagree..."}}
    assert debate_subgraph._should_continue_debate(state) == "Manager"

def test_debate_subgraph_execution(debate_subgraph, mock_llms):
    """测试辩论子图执行流程"""
    quick_llm, deep_llm = mock_llms
    
    # Mock create_bull_researcher 等函数，因为它们内部会调用 LLM
    with patch("tradingagents.agents.create_bull_researcher") as mock_bull, \
         patch("tradingagents.agents.create_bear_researcher") as mock_bear, \
         patch("tradingagents.agents.create_research_manager") as mock_mgr:
        
        # 定义模拟节点的行为
        def bull_node(state):
            count = state.get("investment_debate_state", {}).get("count", 0)
            return {"investment_debate_state": {"count": count + 1, "current_response": "Bull: Buy!"}}
        
        def bear_node(state):
            count = state.get("investment_debate_state", {}).get("count", 0)
            return {"investment_debate_state": {"count": count + 1, "current_response": "Bear: Sell!"}}
            
        def mgr_node(state):
            return {"investment_plan": "Final Plan"}
            
        mock_bull.return_value = bull_node
        mock_bear.return_value = bear_node
        mock_mgr.return_value = mgr_node
        
        graph = debate_subgraph.compile()
        
        initial_state = {
            "investment_debate_state": {"count": 0, "current_response": ""},
            "messages": []
        }
        
        result = graph.invoke(initial_state)
        
        assert result["investment_plan"] == "Final Plan"
        assert result["investment_debate_state"]["count"] >= 2
