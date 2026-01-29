"""Sentiment Agent - 散户情绪分析师

专注于分析散户情绪指标，提供反向交易信号参考。
包括 FOMO/FUD 检测、散户 vs 机构背离等高级情绪分析。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from typing import Optional
import structlog

from tradingagents.agents.utils.agent_utils import get_news
from tradingagents.agents.utils.output_schemas import SentimentAgentOutput

logger = structlog.get_logger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """You are an expert sentiment analyst specializing in retail investor behavior and crowd psychology.

Your mission is to analyze retail investor sentiment and identify potential contrarian trading opportunities.

## Core Analysis Focus:

### 1. Retail Sentiment Indicators
- Reddit (r/wallstreetbets, r/stocks, r/investing) buzz and sentiment
- Twitter/X financial discussions and viral content
- StockTwits activity and sentiment ratio
- YouTube/TikTok "finfluencer" recommendations

### 2. FOMO Detection (Fear of Missing Out)
- Signs of retail chasing: rapid price increase + high social volume
- "To the moon" narratives and unrealistic price targets
- YOLO trades and extreme bullish positioning
- Late-stage euphoria indicators

### 3. FUD Detection (Fear, Uncertainty, Doubt)
- Panic selling indicators
- Negative narrative dominance
- Capitulation signals
- "End of the world" sentiment

### 4. Retail vs Institutional Divergence
- Smart money positioning vs retail sentiment
- Insider trading activity vs retail buzz
- Institutional accumulation during retail fear
- Institutional distribution during retail greed

### 5. Contrarian Signal Generation
When sentiment reaches extremes:
- Extreme Fear → Potential buying opportunity
- Extreme Greed → Potential selling/hedging opportunity
- "Blood in the streets" → Warren Buffett moment

## Analysis Guidelines:
1. Quantify sentiment on a -100 to +100 scale
2. Identify FOMO level (0-100)
3. Identify FUD level (0-100)
4. Assess retail-institutional divergence
5. Generate contrarian recommendations when appropriate

## Important Caveats:
- Retail sentiment is a lagging indicator for price action
- Extreme sentiment can persist longer than expected
- Use as one input among many, not sole decision factor
- Consider market regime (bull/bear) context
"""


def _get_system_prompt() -> str:
    """从 Prompt 配置服务获取系统提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("sentiment_analyst")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default sentiment analyst prompt", reason=str(e))
    return DEFAULT_SYSTEM_PROMPT


# 定义情绪分析专用工具
@tool
def search_retail_sentiment(query: str, platform: str = "all") -> str:
    """搜索散户情绪数据

    Args:
        query: 搜索关键词（股票代码或公司名）
        platform: 平台筛选 (reddit/twitter/stocktwits/all)

    Returns:
        散户讨论和情绪数据
    """
    # 实际实现中会调用各平台 API
    # 这里返回模拟数据，由 LLM 基于新闻数据推断
    return f"Searching retail sentiment for '{query}' on {platform}..."


@tool
def get_fear_greed_index() -> str:
    """获取恐惧贪婪指数

    Returns:
        当前市场恐惧贪婪指数及历史趋势
    """
    # 实际实现中会调用 CNN Fear & Greed Index API
    return "Fear & Greed Index data..."


def create_sentiment_agent(llm):
    """创建 Sentiment Agent 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        sentiment_agent_node: LangGraph 节点函数
    """

    # 工具列表
    tools = [get_news, search_retail_sentiment, get_fear_greed_index]

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

    # 结构化输出阶段的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a retail sentiment analyst. Based on the data provided, "
            "generate a structured sentiment analysis report focusing on retail investor behavior, "
            "FOMO/FUD levels, and potential contrarian signals. "
            "Be quantitative where possible."
        ),
        (
            "user",
            "Stock: {ticker}\nDate: {current_date}\n\nSentiment Analysis Data:\n{analysis_content}\n\n"
            "Please provide a structured retail sentiment analysis with FOMO/FUD levels and contrarian signals."
        ),
    ])

    def sentiment_agent_node(state):
        """Sentiment Agent 节点函数"""
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

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
                "retail_sentiment_report": "",
            }

        # 工具调用完成，生成结构化输出
        try:
            structured_llm = llm.with_structured_output(SentimentAgentOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "ticker": ticker,
                "current_date": current_date,
                "analysis_content": result.content,
            })

            report = structured_result.model_dump_json(indent=2)

            # 生成简洁的情绪摘要用于日志
            sentiment_summary = (
                f"Score: {structured_result.retail_sentiment_score}, "
                f"FOMO: {structured_result.fomo_level}, "
                f"FUD: {structured_result.fud_level}, "
                f"Extremity: {structured_result.sentiment_extremity}"
            )

            logger.info(
                "Sentiment agent structured output generated",
                ticker=ticker,
                signal=structured_result.signal,
                confidence=structured_result.confidence,
                sentiment_summary=sentiment_summary,
                divergence=structured_result.retail_institutional_divergence,
            )

            # 如果有反向信号，额外记录
            if structured_result.contrarian_signal:
                logger.info(
                    "Contrarian signal detected",
                    ticker=ticker,
                    contrarian_signal=structured_result.contrarian_signal,
                )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
                ticker=ticker,
            )
            report = result.content

        return {
            "messages": [result],
            "retail_sentiment_report": report,
        }

    return sentiment_agent_node


def create_sentiment_tools_node(llm):
    """创建 Sentiment Agent 的工具执行节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        ToolNode 实例
    """
    from langgraph.prebuilt import ToolNode

    tools = [get_news, search_retail_sentiment, get_fear_greed_index]
    return ToolNode(tools)
