"""Bear researcher agent plugin."""

from typing import Any, Callable, List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from ..plugin_base import AgentPlugin, AgentRole, AgentCapability


class BearResearcherPlugin(AgentPlugin):
    """Bear researcher agent for building bearish investment cases."""
    
    @property
    def name(self) -> str:
        return "bear_researcher"
    
    @property
    def role(self) -> AgentRole:
        return AgentRole.RESEARCHER
    
    @property
    def capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.BEAR_RESEARCH]
    
    @property
    def prompt_template(self) -> str:
        return """You are a Bear Analyst making the case against investing in the stock. Your goal is to present a well-reasoned argument emphasizing risks, challenges, and negative indicators. Leverage the provided research and data to highlight potential downsides and counter bullish arguments effectively.

Key points to focus on:

- Risks and Challenges: Highlight factors like market saturation, financial instability, or macroeconomic threats that could hinder the stock's performance.
- Competitive Weaknesses: Emphasize vulnerabilities such as weaker market positioning, declining innovation, or threats from competitors.
- Negative Indicators: Use evidence from financial data, market trends, or recent adverse news to support your position.
- Bull Counterpoints: Critically analyze the bull argument with specific data and sound reasoning, exposing weaknesses or over-optimistic assumptions.
- Engagement: Present your argument in a conversational style, directly engaging with the bull analyst's points and debating effectively rather than simply listing facts.

Resources available:

Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history of the debate: {history}
Last bull argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}
Use this information to deliver a compelling bear argument, refute the bull's claims, and engage in a dynamic debate that demonstrates the risks and weaknesses of investing in the stock. You must also address reflections and learn from lessons and mistakes you made in the past."""
    
    @property
    def description(self) -> str:
        return "Bear researcher building bearish investment cases"
    
    @property
    def requires_memory(self) -> bool:
        return True
    
    @property
    def memory_name(self) -> Optional[str]:
        return "bear_memory"
    
    @property
    def llm_type(self) -> str:
        return "quick"
    
    def create_node(
        self,
        llm: BaseChatModel,
        memory: Optional[Any] = None,
        **kwargs
    ) -> Callable:
        """Create the bear researcher node function."""
        def bear_node(state) -> dict:
            investment_debate_state = state["investment_debate_state"]
            history = investment_debate_state.get("history", "")
            bear_history = investment_debate_state.get("bear_history", "")
            
            current_response = investment_debate_state.get("current_response", "")
            market_research_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]
            
            curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
            past_memories = memory.get_memories(curr_situation, n_matches=2) if memory else []
            
            past_memory_str = ""
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
            
            prompt = f"""You are a Bear Analyst making the case against investing in the stock. Your goal is to present a well-reasoned argument emphasizing risks, challenges, and negative indicators. Leverage the provided research and data to highlight potential downsides and counter bullish arguments effectively.

Key points to focus on:

- Risks and Challenges: Highlight factors like market saturation, financial instability, or macroeconomic threats that could hinder the stock's performance.
- Competitive Weaknesses: Emphasize vulnerabilities such as weaker market positioning, declining innovation, or threats from competitors.
- Negative Indicators: Use evidence from financial data, market trends, or recent adverse news to support your position.
- Bull Counterpoints: Critically analyze the bull argument with specific data and sound reasoning, exposing weaknesses or over-optimistic assumptions.
- Engagement: Present your argument in a conversational style, directly engaging with the bull analyst's points and debating effectively rather than simply listing facts.

Resources available:

Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history of the debate: {history}
Last bull argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}
Use this information to deliver a compelling bear argument, refute the bull's claims, and engage in a dynamic debate that demonstrates the risks and weaknesses of investing in the stock. You must also address reflections and learn from lessons and mistakes you made in the past.
"""
            
            response = llm.invoke(prompt)
            
            argument = f"Bear Analyst: {response.content}"
            
            new_investment_debate_state = {
                "history": history + "\n" + argument,
                "bear_history": bear_history + "\n" + argument,
                "bull_history": investment_debate_state.get("bull_history", ""),
                "current_response": argument,
                "count": investment_debate_state["count"] + 1,
            }
            
            return {"investment_debate_state": new_investment_debate_state}
        
        return bear_node
