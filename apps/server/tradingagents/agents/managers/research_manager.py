"""Research Manager - 研究经理

评估投资辩论并做出最终投资决策，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import ResearchManagerOutput

logger = structlog.get_logger(__name__)


def create_research_manager(llm, memory):
    """创建 Research Manager 节点

    Args:
        llm: LangChain LLM 实例
        memory: FinancialSituationMemory 实例

    Returns:
        research_manager_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a research manager. Generate a structured investment decision. "
            "Summarize the bull/bear debate and provide clear reasoning for your decision."
        ),
        (
            "user",
            "Investment Decision Context:\n{decision_context}\n\n"
            "Please provide a structured investment decision."
        ),
    ])

    def research_manager_node(state) -> dict:
        """Research Manager 节点函数"""
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        # 获取向量记忆
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for rec in past_memories:
            past_memory_str += rec["recommendation"] + "\n\n"

        # 原始 prompt
        raw_prompt = f"""As the portfolio manager and debate facilitator, your role is to critically evaluate this round of debate and make a definitive decision: align with the bear analyst, the bull analyst, or choose Hold only if it is strongly justified based on the arguments presented.

Summarize the key points from both sides concisely, focusing on the most compelling evidence or reasoning. Your recommendation—Buy, Sell, or Hold—must be clear and actionable. Avoid defaulting to Hold simply because both sides have valid points; commit to a stance grounded in the debate's strongest arguments.

Additionally, develop a detailed investment plan for the trader. This should include:

Your Recommendation: A decisive stance supported by the most convincing arguments.
Rationale: An explanation of why these arguments lead to your conclusion.
Strategic Actions: Concrete steps for implementing the recommendation.

Take into account your past mistakes on similar situations:
"{past_memory_str}"

Here is the debate:
Debate History:
{history}"""

        # 第一阶段：获取原始决策
        raw_response = llm.invoke(raw_prompt)
        raw_content = raw_response.content

        # 第二阶段：结构化输出
        try:
            structured_llm = llm.with_structured_output(ResearchManagerOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "decision_context": raw_content,
            })

            # 将结构化结果转为 JSON
            structured_json = structured_result.model_dump_json(indent=2)

            # 组合最终输出
            final_content = f"{raw_content}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Research manager structured output generated",
                decision=structured_result.decision,
                winner=structured_result.winner,
                confidence=structured_result.confidence,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            final_content = raw_content

        # 更新辩论状态
        new_investment_debate_state = {
            "judge_decision": final_content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": final_content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": final_content,
        }

    return research_manager_node
