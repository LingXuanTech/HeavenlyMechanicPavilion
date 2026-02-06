"""Vision Analyst Agent - 多模态图表分析

通过 Vision 模型识别和分析财报截图、K线图等金融图表。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are an expert financial chart analyst with Vision capabilities.

Your mission is to analyze financial charts, earnings screenshots, and technical analysis images
to extract actionable insights.

## Core Capabilities:

### 1. Chart Recognition
- K-line/Candlestick charts
- Line charts (price, volume, indicators)
- Bar charts (earnings, revenue)
- Financial statement screenshots
- Technical indicator overlays

### 2. Pattern Recognition
- Head and shoulders, double top/bottom
- Triangle patterns (ascending, descending, symmetrical)
- Flag and pennant patterns
- Cup and handle
- Support and resistance levels

### 3. Data Extraction
- Price levels and ranges
- Volume patterns
- Key financial metrics from screenshots
- Trend lines and moving averages

### 4. Analysis Output
- Chart type identification
- Key data points extraction
- Trend analysis
- Pattern identification
- Risk assessment based on visual data

## Guidelines:
1. Be specific about what you observe
2. Quantify observations where possible
3. Note any limitations in image quality
4. Cross-reference with known market context
"""


def create_vision_analyst_agent(llm):
    """创建 Vision Analyst Agent 节点

    Args:
        llm: LangChain LLM 实例（需支持 Vision）

    Returns:
        vision_analyst_node: LangGraph 节点函数
    """

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            DEFAULT_SYSTEM_PROMPT
            + "\nFor your reference, the current date is {current_date}. "
            "The stock we want to analyze is {ticker}.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    def vision_analyst_node(state):
        """Vision Analyst Agent 节点函数"""
        current_date = state.get("trade_date", "")
        ticker = state.get("company_of_interest", "")

        # Vision Agent 主要通过外部 API 调用工作
        # 在分析流程中，它处理已上传的图片数据
        vision_data = state.get("vision_data", "")

        if not vision_data:
            report = (
                f"No visual data provided for {ticker}. "
                "Vision analysis requires uploaded images (charts, screenshots). "
                "Skipping vision analysis."
            )
            return {
                "messages": state.get("messages", []),
                "vision_report": report,
            }

        # 构建分析请求
        formatted_prompt = prompt.partial(
            current_date=current_date,
            ticker=ticker,
        )

        chain = formatted_prompt | llm
        result = chain.invoke(state["messages"])

        report = result.content

        logger.info(
            "Vision analyst completed",
            ticker=ticker,
            report_length=len(report),
        )

        return {
            "messages": [result],
            "vision_report": report,
        }

    return vision_analyst_node
