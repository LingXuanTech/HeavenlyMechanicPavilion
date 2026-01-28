"""Fundamentals Analyst - 基本面分析师

分析公司财务数据和基本面信息，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import structlog

from tradingagents.agents.utils.agent_utils import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
)
from tradingagents.agents.utils.output_schemas import FundamentalsAnalystOutput

logger = structlog.get_logger(__name__)


def create_fundamentals_analyst(llm):
    """创建 Fundamentals Analyst 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        fundamentals_analyst_node: LangGraph 节点函数
    """

    # 工具列表
    tools = [
        get_fundamentals,
        get_balance_sheet,
        get_cashflow,
        get_income_statement,
    ]

    # 系统提示词
    system_message = """You are a researcher tasked with analyzing fundamental information about a company.

Your objective is to write a comprehensive report covering:
1. Company profile and business overview
2. Financial statements analysis (Balance Sheet, Income Statement, Cash Flow)
3. Key financial ratios (P/E, P/B, ROE, ROA, Debt/Equity, etc.)
4. Revenue and earnings trends
5. Profitability and efficiency metrics
6. Liquidity and solvency assessment
7. Growth indicators and outlook

Use the available tools:
- get_fundamentals: Comprehensive company financial data
- get_balance_sheet: Assets, liabilities, and equity details
- get_cashflow: Operating, investing, and financing activities
- get_income_statement: Revenue, expenses, and profitability

Provide detailed, fine-grained analysis with specific numbers and comparisons. Avoid vague statements like "trends are mixed" - instead, explain exactly what the data shows and its implications for investors.
"""

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
            "You are a fundamentals analyst. Based on the financial data provided, "
            "generate a structured analysis report. Include specific metrics and values."
        ),
        (
            "user",
            "Stock: {ticker}\nDate: {current_date}\n\nFinancial Analysis Data:\n{analysis_content}\n\n"
            "Please provide a structured fundamentals analysis."
        ),
    ])

    def fundamentals_analyst_node(state):
        """Fundamentals Analyst 节点函数"""
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
                "fundamentals_report": "",
            }

        # 工具调用完成，生成结构化输出
        try:
            structured_llm = llm.with_structured_output(FundamentalsAnalystOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "ticker": ticker,
                "current_date": current_date,
                "analysis_content": result.content,
            })

            report = structured_result.model_dump_json(indent=2)

            logger.info(
                "Fundamentals analyst structured output generated",
                ticker=ticker,
                signal=structured_result.signal,
                confidence=structured_result.confidence,
                valuation=structured_result.valuation_status,
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
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
