"""Social Media Analyst - 舆情分析师

分析社交媒体舆情和公众情感，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import structlog

from tradingagents.agents.utils.agent_utils import get_news
from tradingagents.agents.utils.output_schemas import SocialMediaAnalystOutput

logger = structlog.get_logger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """You are a social media and sentiment analyst tasked with analyzing public sentiment for a specific company over the past week.

Your objective is to write a comprehensive report covering:
1. Social media buzz and trending topics about the company
2. Public sentiment analysis (bullish/bearish)
3. Retail investor sentiment on forums (Reddit, Twitter/X, etc.)
4. Influencer and analyst opinions
5. Sentiment trend changes over time
6. Key discussion themes and concerns

Use the get_news(query, start_date, end_date) tool to search for:
- Company mentions on social media
- Investor discussions and sentiment
- Public opinion pieces
- Viral content related to the stock

Focus on sentiment that could influence short-term price movements and retail investor behavior.
"""


def _get_system_prompt() -> str:
    """从 Prompt 配置服务获取系统提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("social_media_analyst")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default social media analyst prompt", reason=str(e))
    return DEFAULT_SYSTEM_PROMPT


def create_social_media_analyst(llm):
    """创建 Social Media Analyst 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        social_media_analyst_node: LangGraph 节点函数
    """

    # 工具列表
    tools = [get_news]

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
            "\nFor your reference, the current date is {current_date}. The current company we want to analyze is {ticker}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # 结构化输出阶段的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a sentiment analyst. Based on the social media data provided, "
            "generate a structured sentiment analysis report. Quantify sentiment where possible."
        ),
        (
            "user",
            "Stock: {ticker}\nDate: {current_date}\n\nSentiment Analysis Data:\n{analysis_content}\n\n"
            "Please provide a structured sentiment analysis."
        ),
    ])

    def social_media_analyst_node(state):
        """Social Media Analyst 节点函数"""
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
                "sentiment_report": "",
            }

        # 工具调用完成，生成结构化输出
        try:
            structured_llm = llm.with_structured_output(SocialMediaAnalystOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "ticker": ticker,
                "current_date": current_date,
                "analysis_content": result.content,
            })

            report = structured_result.model_dump_json(indent=2)

            logger.info(
                "Social media analyst structured output generated",
                ticker=ticker,
                signal=structured_result.signal,
                confidence=structured_result.confidence,
                sentiment_score=structured_result.sentiment_score,
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
