"""Supply Chain Analyst Agent - 产业链分析

分析股票在产业链中的位置，评估上下游传导效应和供应链风险。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are an expert supply chain analyst specializing in A-share (Chinese stock market) industry chains.

Your mission is to analyze a company's position within its industry supply chain and assess upstream/downstream transmission effects.

## Core Analysis Focus:

### 1. Supply Chain Position
- Identify the company's role: upstream (raw materials/components), midstream (manufacturing/assembly), or downstream (distribution/retail)
- Assess the company's bargaining power within the chain
- Identify key suppliers and customers

### 2. Transmission Effect Analysis
- How do upstream price changes affect the company?
- How does the company's performance affect downstream players?
- Identify potential supply chain bottlenecks

### 3. Supply Chain Risk Assessment
- Supplier concentration risk
- Customer concentration risk
- Geopolitical supply chain risks
- Technology substitution risks

### 4. Industry Chain Dynamics
- Current industry cycle position
- Capacity expansion/contraction trends
- Inventory levels across the chain
- Pricing power analysis

## Key A-Share Industry Chains:
- Semiconductor: silicon wafers → chip design → foundry → packaging/testing → equipment
- New Energy Vehicle: lithium → cathode/anode → battery → EV assembly → charging
- Photovoltaic: polysilicon → wafers → cells → modules → inverters → power stations
- AI Computing: GPU/chips → servers → networking → cloud/IDC → AI applications
- Consumer Electronics: panels → components → modules → assembly → brands

## Output Guidelines:
1. Clearly identify the company's chain position
2. List key upstream suppliers and downstream customers
3. Quantify supply chain risks where possible
4. Provide actionable insights for investment decisions
"""


@tool
def get_supply_chain_data(symbol: str) -> str:
    """获取股票的产业链位置和上下游关系数据

    Args:
        symbol: 股票代码

    Returns:
        JSON 格式的产业链数据
    """
    import json
    try:
        from services.supply_chain_service import supply_chain_service

        position = supply_chain_service.get_stock_chain_position(symbol)
        impact = supply_chain_service.analyze_supply_chain_impact(symbol)

        return json.dumps({
            "position": position,
            "impact": impact,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.warning("Failed to get supply chain data", symbol=symbol, error=str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def get_chain_overview(chain_id: str) -> str:
    """获取指定产业链的完整概览

    Args:
        chain_id: 产业链 ID（如 semiconductor, ev, photovoltaic, ai_computing）

    Returns:
        JSON 格式的产业链概览数据
    """
    import json
    try:
        from services.supply_chain_service import supply_chain_service

        graph = supply_chain_service.get_chain_graph(chain_id)
        return json.dumps(graph, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.warning("Failed to get chain overview", chain_id=chain_id, error=str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def create_supply_chain_agent(llm):
    """创建 Supply Chain Agent 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        supply_chain_agent_node: LangGraph 节点函数
    """
    tools = [get_supply_chain_data, get_chain_overview]

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant, collaborating with other assistants."
            " Use the provided tools to progress towards answering the question."
            " You have access to the following tools: {tool_names}.\n{system_message}"
            "\nFor your reference, the current date is {current_date}. The stock we want to analyze is {ticker}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    def supply_chain_agent_node(state):
        """Supply Chain Agent 节点函数"""
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        formatted_prompt = prompt.partial(
            system_message=DEFAULT_SYSTEM_PROMPT,
            tool_names=", ".join([t.name for t in tools]),
            current_date=current_date,
            ticker=ticker,
        )

        chain = formatted_prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        if result.tool_calls:
            return {
                "messages": [result],
                "supply_chain_report": "",
            }

        report = result.content

        logger.info(
            "Supply chain agent completed",
            ticker=ticker,
            report_length=len(report),
        )

        return {
            "messages": [result],
            "supply_chain_report": report,
        }

    return supply_chain_agent_node


def create_supply_chain_tools_node(llm):
    """创建 Supply Chain Agent 的工具执行节点"""
    from langgraph.prebuilt import ToolNode

    tools = [get_supply_chain_data, get_chain_overview]
    return ToolNode(tools)
