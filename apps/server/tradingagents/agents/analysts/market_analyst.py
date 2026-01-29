"""Market Analyst - 市场分析师

使用技术指标分析股票市场趋势，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import structlog

from tradingagents.agents.utils.agent_utils import get_stock_data, get_indicators
from tradingagents.agents.utils.output_schemas import MarketAnalystOutput

logger = structlog.get_logger(__name__)

# 默认系统提示词（当 prompt_config_service 不可用时使用）
DEFAULT_SYSTEM_MESSAGE = """You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy from the following list. The goal is to choose up to **8 indicators** that provide complementary insights without redundancy.

Categories and each category's indicators are:

Moving Averages:
- close_50_sma: 50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance.
- close_200_sma: 200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups.
- close_10_ema: 10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points.

MACD Related:
- macd: MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes.
- macds: MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades.
- macdh: MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early.

Momentum Indicators:
- rsi: RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals.

Volatility Indicators:
- boll: Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands.
- boll_ub: Bollinger Upper Band: Typically 2 standard deviations above the middle line. Signals potential overbought conditions.
- boll_lb: Bollinger Lower Band: Typically 2 standard deviations below the middle line. Indicates potential oversold conditions.
- atr: ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes.

Volume-Based Indicators:
- vwma: VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data.

Instructions:
1. First call get_stock_data to retrieve the stock CSV data
2. Then use get_indicators with specific indicator names
3. Analyze the data and provide detailed insights
4. Select indicators that provide diverse and complementary information
5. Avoid redundancy (e.g., do not select both RSI and StochRSI)
"""


def _get_system_message() -> str:
    """从 Prompt 配置服务获取系统提示词，失败时使用默认值"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("market_analyst")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default system message", reason=str(e))
    return DEFAULT_SYSTEM_MESSAGE


def create_market_analyst(llm):
    """创建 Market Analyst 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        market_analyst_node: LangGraph 节点函数
    """

    # 工具列表
    tools = [get_stock_data, get_indicators]

    # 从配置服务获取系统提示词（支持动态配置）
    system_message = _get_system_message()

    # 数据收集阶段的 prompt
    collection_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant, collaborating with other assistants."
            " Use the provided tools to progress towards answering the question."
            " If you are unable to fully answer, that's OK; another assistant with different tools"
            " will help where you left off. Execute what you can to make progress."
            " You have access to the following tools: {tool_names}.\n{system_message}"
            "\nFor your reference, the current date is {current_date}. The company we want to analyze is {ticker}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # 结构化输出阶段的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a market analyst. Based on the technical analysis data provided, "
            "generate a structured analysis report. Be specific about the indicators and their values."
        ),
        (
            "user",
            "Stock: {ticker}\nDate: {current_date}\n\nAnalysis Data:\n{analysis_content}\n\n"
            "Please provide a structured market analysis."
        ),
    ])

    def market_analyst_node(state):
        """Market Analyst 节点函数"""
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
                "market_report": "",
            }

        # 工具调用完成，生成结构化输出
        try:
            # 使用 with_structured_output 生成结构化报告
            structured_llm = llm.with_structured_output(MarketAnalystOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "ticker": ticker,
                "current_date": current_date,
                "analysis_content": result.content,
            })

            # 将结构化结果转为 JSON 字符串存储
            report = structured_result.model_dump_json(indent=2)

            logger.info(
                "Market analyst structured output generated",
                ticker=ticker,
                signal=structured_result.signal,
                confidence=structured_result.confidence,
            )

        except Exception as e:
            # 降级：如果结构化输出失败，使用原始内容
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
                ticker=ticker,
            )
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
