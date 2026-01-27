from langchain_core.prompts import ChatPromptTemplate
from services.prompt_manager import prompt_manager
from services.data_router import MarketRouter
import structlog

logger = structlog.get_logger()

def create_portfolio_agent(llm):
    async def portfolio_agent_node(state):
        logger.info("Portfolio agent analyzing")
        
        # In a real scenario, we would fetch the user's watchlist or portfolio from DB
        # For now, we assume it's passed in state or we fetch it here
        watchlist = state.get("watchlist", [])
        
        prompt_data = prompt_manager.get_prompt("portfolio_agent", {"watchlist": str(watchlist)})
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system"]),
            ("user", f"当前关注列表：{watchlist}。请分析组合风险。")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({})
        
        return {
            "portfolio_report": response.content
        }
    
    return portfolio_agent_node
