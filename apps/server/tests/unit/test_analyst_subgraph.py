import pytest
from unittest.mock import MagicMock, patch
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode

from tradingagents.graph.subgraphs.analyst_subgraph import AnalystSubGraph
from tradingagents.agents.utils.agent_states import AgentState

class MockConditionalLogic:
    def should_continue_market(self, state):
        return "Clear Market"
    def should_continue_news(self, state):
        return "Clear News"
    def should_continue_fundamentals(self, state):
        return "Clear Fundamentals"

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=ChatOpenAI)
    llm.invoke.return_value = AIMessage(content="Mocked analyst report")
    llm.bind_tools.return_value = llm
    return llm

@pytest.fixture
def mock_tool_nodes():
    return {
        "market": MagicMock(spec=ToolNode),
        "news": MagicMock(spec=ToolNode),
        "fundamentals": MagicMock(spec=ToolNode),
    }

@pytest.fixture
def analyst_subgraph(mock_llm, mock_tool_nodes):
    conditional_logic = MockConditionalLogic()
    selected_analysts = ["market", "news", "fundamentals"]
    return AnalystSubGraph(
        quick_thinking_llm=mock_llm,
        tool_nodes=mock_tool_nodes,
        conditional_logic=conditional_logic,
        selected_analysts=selected_analysts,
        enable_resilience=True
    )

def test_analyst_subgraph_initialization(analyst_subgraph):
    """测试 AnalystSubGraph 初始化"""
    assert analyst_subgraph.llm is not None
    assert len(analyst_subgraph.selected_analysts) == 3
    assert "market" in analyst_subgraph.selected_analysts

def test_analyst_subgraph_compile(analyst_subgraph):
    """测试子图编译"""
    graph = analyst_subgraph.compile()
    assert graph is not None
    # 检查节点是否存在
    nodes = graph.nodes
    assert "Router" in nodes
    assert "Sync" in nodes
    assert "Market Analyst" in nodes
    assert "News Analyst" in nodes
    assert "Fundamentals Analyst" in nodes

def test_analyst_subgraph_execution_flow(analyst_subgraph, mock_llm):
    """测试分析师子图执行流程"""
    # Mock 掉具体的分析师节点，避免复杂的内部逻辑
    with patch("tradingagents.agents.create_market_analyst") as m1, \
         patch("tradingagents.agents.create_news_analyst") as m2, \
         patch("tradingagents.agents.create_fundamentals_analyst") as m3, \
         patch("tradingagents.agents.create_msg_delete") as md, \
         patch("tradingagents.graph.conditional_logic.ConditionalLogic.should_continue_market") as mock_cond_m, \
         patch("tradingagents.graph.conditional_logic.ConditionalLogic.should_continue_news") as mock_cond_n, \
         patch("tradingagents.graph.conditional_logic.ConditionalLogic.should_continue_fundamentals") as mock_cond_f:
        
        # 返回不带 tool_calls 的消息，避免条件逻辑错误
        m1.return_value = lambda s: {"market_report": "ok", "messages": [AIMessage(content="Market analysis done")]}
        m2.return_value = lambda s: {"news_report": "ok", "messages": [AIMessage(content="News analysis done")]}
        m3.return_value = lambda s: {"fundamentals_report": "ok", "messages": [AIMessage(content="Fundamentals analysis done")]}
        # 返回一个不执行任何操作的节点，避免 RemoveMessage 导致的 ID 错误
        md.return_value = lambda s: {}
        
        # Mock 条件逻辑，直接跳过工具调用
        mock_cond_m.return_value = "Msg Clear Market"
        mock_cond_n.return_value = "Msg Clear News"
        mock_cond_f.return_value = "Msg Clear Fundamentals"
        
        graph = analyst_subgraph.compile()
        
        initial_state = {
            "messages": [AIMessage(content="Analyze AAPL")],
            "company_of_interest": "AAPL",
            "trade_date": "2026-02-06",
            "market": "US",
            "recommended_analysts": ["market", "news", "fundamentals"]
        }
        
        result = graph.invoke(initial_state)
        
        assert "messages" in result
        # 验证同步消息已添加
        assert any("All analysts completed" in m.content for m in result.get("messages", []) if hasattr(m, 'content'))

def test_analyst_subgraph_error_handling(analyst_subgraph, mock_llm):
    """测试分析师子图的错误处理和降级机制"""
    # 模拟 Market 分析师失败
    with patch("tradingagents.graph.resilience.AnalystNodeFactory.wrap_analyst_node") as mock_wrap, \
         patch("tradingagents.agents.create_news_analyst") as m2, \
         patch("tradingagents.agents.create_fundamentals_analyst") as m3, \
         patch("tradingagents.agents.create_msg_delete") as md, \
         patch("tradingagents.graph.conditional_logic.ConditionalLogic.should_continue_news") as mock_cond_n, \
         patch("tradingagents.graph.conditional_logic.ConditionalLogic.should_continue_fundamentals") as mock_cond_f:
        
        md.return_value = lambda s: {}
        
        def side_effect(node, analyst_type, timeout):
            if analyst_type == "market":
                def error_node(state):
                    return {"_analyst_errors": {"market": "Timeout error"}, "messages": [AIMessage(content="Error")]}
                return error_node
            return node
        
        mock_wrap.side_effect = side_effect
        m2.return_value = lambda s: {"news_report": "ok", "messages": [AIMessage(content="News done")]}
        m3.return_value = lambda s: {"fundamentals_report": "ok", "messages": [AIMessage(content="Fundamentals done")]}
        
        # Mock 条件逻辑
        mock_cond_n.return_value = "Msg Clear News"
        mock_cond_f.return_value = "Msg Clear Fundamentals"
        
        # 重新编译以应用 Mock
        graph = analyst_subgraph.compile()
        
        initial_state = {
            "messages": [AIMessage(content="Analyze AAPL")],
            "company_of_interest": "AAPL",
            "trade_date": "2026-02-06",
            "_analyst_errors": {},
            "_analyst_completed": []
        }
        
        result = graph.invoke(initial_state)
        
        # 验证即使 market 失败，流程依然完成
        assert any("Note: 1 analyst(s) had errors" in m.content for m in result.get("messages", []) if hasattr(m, 'content'))

def test_analyst_subgraph_parallel_execution(analyst_subgraph):
    """验证分析师节点的并行执行能力（通过检查图结构）"""
    graph = analyst_subgraph.compile()
    
    # 获取图的结构
    # 在 LangGraph 中，graph.builder.edges 是 Edge 对象的列表
    # 如果 builder.edges 是 tuple 列表，我们需要按索引访问
    edges = graph.builder.edges
    
    # 验证 Router 指向多个分析师
    # Edge 可能是 (source, target, ...) 格式 of tuple
    router_out_edges = [e for e in edges if e[0] == "Router"]
    targets = [e[1] for e in router_out_edges]
    
    assert "Market Analyst" in targets
    assert "News Analyst" in targets
    assert "Fundamentals Analyst" in targets
    
    # 验证多个 Clear 节点指向 Sync
    sync_in_edges = [e for e in edges if e[1] == "Sync"]
    sources = [e[0] for e in sync_in_edges]
    
    assert "Clear Market" in sources
    assert "Clear News" in sources
    assert "Clear Fundamentals" in sources
