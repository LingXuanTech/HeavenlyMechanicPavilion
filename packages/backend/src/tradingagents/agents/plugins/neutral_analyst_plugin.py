"""Neutral analyst agent plugin."""

from typing import Any, Callable, List, Optional

from langchain_core.language_models import BaseChatModel

from ..plugin_base import AgentCapability, AgentPlugin, AgentRole


class NeutralAnalystPlugin(AgentPlugin):
    """Neutral analyst agent for balanced risk perspectives."""

    @property
    def name(self) -> str:
        return "neutral_analyst"

    @property
    def role(self) -> AgentRole:
        return AgentRole.RISK_ANALYST

    @property
    def capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.NEUTRAL_ANALYSIS]

    @property
    def prompt_template(self) -> str:
        return """As the Neutral Risk Analyst, you represent a balanced perspective, weighing both potential gains and risks while advocating for sustainable growth."""

    @property
    def description(self) -> str:
        return "Neutral analyst advocating for balanced risk strategies"

    @property
    def llm_type(self) -> str:
        return "quick"

    def create_node(self, llm: BaseChatModel, memory: Optional[Any] = None, **kwargs) -> Callable:
        """Create the neutral analyst node function."""

        def neutral_node(state) -> dict:
            risk_debate_state = state["risk_debate_state"]
            history = risk_debate_state.get("history", "")
            neutral_history = risk_debate_state.get("neutral_history", "")

            current_risky_response = risk_debate_state.get("current_risky_response", "")
            current_safe_response = risk_debate_state.get("current_safe_response", "")

            market_research_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]

            trader_decision = state["trader_investment_plan"]

            prompt = f"""As the Neutral Risk Analyst, you represent a balanced perspective, weighing both potential gains and risks while advocating for sustainable growth. Your role is to assess the trader's decision with a practical, realistic lens, finding middle ground between the aggressive and conservative approaches. Here is the trader's decision:

{trader_decision}

Evaluate this decision by responding to arguments from both the Risky and Safe Analysts, offering critiques and adjustments that balance risk and reward. Draw on the following data to support your balanced position:

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}
Here is the current conversation history: {history} Here is the last response from the risky analyst: {current_risky_response} Here is the last response from the safe analyst: {current_safe_response}. If there are no responses from the other viewpoints, do not halluncinate and just present your point.

Challenge both extremes: point out where the Risky Analyst's enthusiasm may be unrealistic and where the Safe Analyst's caution may be excessive. Engage in active debate, highlighting the merits of moderation and pragmatic decision-making. Output conversationally as if you are speaking without any special formatting."""

            response = llm.invoke(prompt)

            argument = f"Neutral Analyst: {response.content}"

            new_risk_debate_state = {
                "history": history + "\n" + argument,
                "neutral_history": neutral_history + "\n" + argument,
                "risky_history": risk_debate_state.get("risky_history", ""),
                "safe_history": risk_debate_state.get("safe_history", ""),
                "latest_speaker": "Neutral",
                "current_neutral_response": argument,
                "current_risky_response": risk_debate_state.get("current_risky_response", ""),
                "current_safe_response": risk_debate_state.get("current_safe_response", ""),
                "count": risk_debate_state["count"] + 1,
            }

            return {"risk_debate_state": new_risk_debate_state}

        return neutral_node
