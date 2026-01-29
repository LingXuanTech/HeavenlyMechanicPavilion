"""Fund Flow Agent - A 股资金流向分析师

专门分析北向资金和龙虎榜数据，判断市场资金动向。
适用于 A 股市场特有的资金流向分析。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Optional
import structlog

from tradingagents.agents.utils.agent_utils import get_news
from tradingagents.agents.utils.china_market_tools import CHINA_MARKET_TOOLS

logger = structlog.get_logger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """You are an expert fund flow analyst specializing in Chinese A-share market capital movements.

Your mission is to analyze institutional and retail capital flows, including:
- North-bound capital (沪深港通北向资金)
- Dragon and Tiger Board (龙虎榜) data
- Institutional vs retail trading patterns

## Core Analysis Focus:

### 1. North-bound Capital (北向资金)
- Daily net inflow/outflow amounts
- Shanghai Connect vs Shenzhen Connect distribution
- Individual stock holding changes
- Cumulative trends (weekly/monthly)
- Major position changes by foreign institutions

### 2. Dragon and Tiger Board (龙虎榜)
- Reasons for appearance (涨停/跌停/换手率)
- Institutional vs retail seats (机构专用 vs 游资席位)
- Famous hot money tracking (溧阳路, 赵老哥, 拉萨天团)
- Net buy/sell rankings
- Historical appearance frequency

### 3. Signal Interpretation
- North + LHB institutional buy = Strong bullish signal
- North outflow + Hot money sell = Bearish signal
- North buy + Hot money chase = Short-term strength, watch profit-taking
- Stable north + Frequent LHB = High volatility, swing trading opportunity

### 4. Key Metrics
- North holding ratio (持股占比)
- Daily change percentage
- Net buy amount (万元/亿元)
- Institution vs hot money divergence

## Analysis Guidelines:
1. Focus on capital flow data, not just price action
2. Distinguish between institutional and retail behavior
3. Consider the signal convergence (北向 + 龙虎榜)
4. Note any unusual activity patterns
5. Provide actionable trading signals based on fund flows

## Important Context:
- A-share market has unique capital flow dynamics
- North-bound capital often leads market sentiment
- Dragon and Tiger Board reveals short-term speculative activity
- Institutional buying is generally more reliable than hot money

## Output Requirements:
- Quantify fund flows in 亿元 (billions CNY)
- Provide clear buy/sell signals
- Rate confidence level (0-100)
- Highlight any divergences or unusual patterns
"""


def _get_system_prompt() -> str:
    """从 Prompt 配置服务获取系统提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("fund_flow_analyst")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default fund flow analyst prompt", reason=str(e))
    return DEFAULT_SYSTEM_PROMPT


def create_fund_flow_agent(llm):
    """创建 Fund Flow Agent 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        fund_flow_agent_node: LangGraph 节点函数
    """

    # 工具列表：使用 china_market_tools.py 中的真实工具
    tools = [get_news] + CHINA_MARKET_TOOLS

    # 从配置服务获取系统提示词
    system_message = _get_system_prompt()

    # 数据收集阶段的 prompt
    collection_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant, collaborating with other assistants."
            " Use the provided tools to progress towards answering the question."
            " If you are unable to fully answer, that's OK; another assistant with different tools"
            " will help where you left off. Execute what you can to make progress."
            " You have access to the following tools: {tool_names}.\n{system_message}"
            "\nFor your reference, the current date is {current_date}. The stock we want to analyze is {ticker}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    def fund_flow_agent_node(state):
        """Fund Flow Agent 节点函数"""
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # 检查是否为 A 股（CN 市场）
        market = state.get("market", "")
        if market and market != "CN":
            logger.info(
                "Fund flow agent skipped for non-CN market",
                ticker=ticker,
                market=market,
            )
            return {
                "messages": [],
                "china_flow_data": '{"summary": "Fund flow analysis is designed for A-share (CN) market only.", "signal": "Hold", "confidence": 50}',
            }

        # 准备 prompt
        prompt = collection_prompt.partial(
            system_message=system_message,
            tool_names=", ".join([tool.name for tool in tools]),
            current_date=current_date,
            ticker=ticker,
        )

        # 绑定工具并调用
        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        # 如果有工具调用，返回让 LangGraph 处理
        if result.tool_calls:
            return {
                "messages": [result],
                "china_flow_data": "",
            }

        # 工具调用完成，保存分析结果
        logger.info(
            "Fund flow agent analysis completed",
            ticker=ticker,
            content_length=len(result.content) if result.content else 0,
        )

        return {
            "messages": [result],
            "china_flow_data": result.content,
        }

    return fund_flow_agent_node


def create_fund_flow_tools_node(llm):
    """创建 Fund Flow Agent 的工具执行节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        ToolNode 实例
    """
    from langgraph.prebuilt import ToolNode

    tools = [get_news] + CHINA_MARKET_TOOLS
    return ToolNode(tools)
