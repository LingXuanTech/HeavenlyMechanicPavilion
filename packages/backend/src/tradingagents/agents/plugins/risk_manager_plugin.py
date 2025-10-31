"""Risk manager agent plugin."""

from typing import Any, Callable, List, Optional

from langchain_core.language_models import BaseChatModel

from ..plugin_base import AgentCapability, AgentPlugin, AgentRole


class RiskManagerPlugin(AgentPlugin):
    """Risk manager agent for final risk assessment and decision."""

    @property
    def name(self) -> str:
        return "risk_manager"

    @property
    def role(self) -> AgentRole:
        return AgentRole.RISK_MANAGER

    @property
    def capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.RISK_MANAGEMENT]

    @property
    def prompt_template(self) -> str:
        return """As the risk manager, make a final decision based on the risk debate."""

    @property
    def description(self) -> str:
        return "Risk manager making final risk-adjusted decisions"

    @property
    def requires_memory(self) -> bool:
        return True

    @property
    def memory_name(self) -> Optional[str]:
        return "risk_manager_memory"

    @property
    def llm_type(self) -> str:
        return "deep"

    def create_node(self, llm: BaseChatModel, memory: Optional[Any] = None, **kwargs) -> Callable:
        """Create the risk manager node function."""

        def risk_manager_node(state) -> dict:
            history = state["risk_debate_state"].get("history", "")
            market_research_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]

            risk_debate_state = state["risk_debate_state"]

            curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
            past_memories = memory.get_memories(curr_situation, n_matches=2) if memory else []

            past_memory_str = ""
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"

            prompt = f"""As the Risk Manager, you must now make a definitive, actionable decision after reviewing the debate among the Risky, Safe, and Neutral Risk Analysts. Your role is to synthesize their arguments, weigh the competing perspectives on risk and reward, and select a final course of action: align with one viewpoint or propose an adjusted plan. Your recommendation should be clear, concise, and supported by the strongest arguments from the debate.

Key responsibilities:

Synthesize Key Arguments: Summarize the main points from each analyst—Risky, Safe, and Neutral—highlighting the most compelling reasoning from each side.
Make a Decisive Recommendation: Choose a final decision (e.g., Buy, Sell, Hold) that is best supported by the analysis. If the debate suggests a modification to the original plan, specify the adjustment.
Justify Your Decision: Explain why the chosen approach is optimal, referencing key evidence and reasoning from the debate.
Provide Strategic Next Steps: Include clear, actionable steps to implement the decision.
Address lessons learned: Consider your past reflections on similar decisions to improve this decision.

Present your decision and rationale conversationally, without special formatting, ensuring it is both strategic and grounded in the analysts' insights.

Here are your past reflections on mistakes:
"{past_memory_str}"

Here is the debate:
Debate History:
{history}"""
            response = llm.invoke(prompt)

            new_risk_debate_state = {
                "judge_decision": response.content,
                "history": risk_debate_state.get("history", ""),
                "risky_history": risk_debate_state.get("risky_history", ""),
                "safe_history": risk_debate_state.get("safe_history", ""),
                "neutral_history": risk_debate_state.get("neutral_history", ""),
                "latest_speaker": "Risk Judge",
                "current_risky_response": risk_debate_state.get("current_risky_response", ""),
                "current_safe_response": risk_debate_state.get("current_safe_response", ""),
                "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
                "count": risk_debate_state["count"],
            }

            return {
                "risk_debate_state": new_risk_debate_state,
                "final_trade_decision": response.content,
            }

        return risk_manager_node
