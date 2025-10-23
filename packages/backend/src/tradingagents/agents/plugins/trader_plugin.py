"""Trader agent plugin."""

from typing import Any, Callable, List, Optional
from langchain_core.language_models import BaseChatModel
import functools

from ..plugin_base import AgentPlugin, AgentRole, AgentCapability


class TraderPlugin(AgentPlugin):
    """Trader agent for making trading decisions."""
    
    @property
    def name(self) -> str:
        return "trader"
    
    @property
    def role(self) -> AgentRole:
        return AgentRole.TRADER
    
    @property
    def capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.TRADING]
    
    @property
    def prompt_template(self) -> str:
        return "You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation. Do not forget to utilize lessons from past decisions to learn from your mistakes. Here is some reflections from similar situations you traded in and the lessons learned: {past_memory_str}"
    
    @property
    def description(self) -> str:
        return "Trader making final trading decisions"
    
    @property
    def requires_memory(self) -> bool:
        return True
    
    @property
    def memory_name(self) -> Optional[str]:
        return "trader_memory"
    
    @property
    def llm_type(self) -> str:
        return "quick"
    
    def create_node(
        self,
        llm: BaseChatModel,
        memory: Optional[Any] = None,
        **kwargs
    ) -> Callable:
        """Create the trader node function."""
        def trader_node(state, name):
            company_name = state["company_of_interest"]
            investment_plan = state["investment_plan"]
            market_research_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]
            
            curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
            past_memories = memory.get_memories(curr_situation, n_matches=2) if memory else []
            
            past_memory_str = ""
            if past_memories:
                for i, rec in enumerate(past_memories, 1):
                    past_memory_str += rec["recommendation"] + "\n\n"
            else:
                past_memory_str = "No past memories found."
            
            context = {
                "role": "user",
                "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision.",
            }
            
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation. Do not forget to utilize lessons from past decisions to learn from your mistakes. Here is some reflections from similar situations you traded in and the lessons learned: {past_memory_str}""",
                },
                context,
            ]
            
            result = llm.invoke(messages)
            
            return {
                "messages": [result],
                "trader_investment_plan": result.content,
                "sender": name,
            }
        
        return functools.partial(trader_node, name="Trader")
