"""Portfolio Agent - 组合分析师

分析投资组合风险和相关性，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from services.prompt_manager import prompt_manager
from tradingagents.agents.utils.output_schemas import PortfolioAnalystOutput

logger = structlog.get_logger(__name__)


def create_portfolio_agent(llm):
    """创建 Portfolio Agent 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        portfolio_agent_node: LangGraph 异步节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a portfolio analyst. Generate a structured portfolio risk analysis report. "
            "Focus on correlation, concentration, and diversification aspects."
        ),
        (
            "user",
            "Watchlist: {watchlist}\n\nPortfolio Analysis:\n{portfolio_context}\n\n"
            "Please provide a structured portfolio analysis."
        ),
    ])

    async def portfolio_agent_node(state):
        """Portfolio Agent 异步节点函数"""
        logger.info("Portfolio agent analyzing")

        # 获取关注列表
        watchlist = state.get("watchlist", [])

        # 获取 prompt 数据
        prompt_data = prompt_manager.get_prompt("portfolio_agent", {"watchlist": str(watchlist)})

        # 第一阶段：获取原始组合分析
        raw_prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system"]),
            ("user", f"当前关注列表：{watchlist}。请分析组合风险。")
        ])

        raw_chain = raw_prompt | llm
        raw_response = await raw_chain.ainvoke({})

        # 第二阶段：结构化输出
        try:
            structured_llm = llm.with_structured_output(PortfolioAnalystOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = await structured_chain.ainvoke({
                "watchlist": str(watchlist),
                "portfolio_context": raw_response.content,
            })

            report = structured_result.model_dump_json(indent=2)

            logger.info(
                "Portfolio analyst structured output generated",
                signal=structured_result.signal,
                confidence=structured_result.confidence,
                correlation_risk=structured_result.correlation_risk,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            report = raw_response.content

        return {
            "portfolio_report": report
        }

    return portfolio_agent_node
