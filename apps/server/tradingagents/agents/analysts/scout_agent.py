from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from services.prompt_manager import prompt_manager
from services.data_router import MarketRouter
import structlog

logger = structlog.get_logger()

def create_scout_agent(llm):
    async def scout_agent_node(state):
        query = state.get("query", "")
        logger.info("Scout agent searching", query=query)
        
        prompt_data = prompt_manager.get_prompt("scout_agent", {"query": query})
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system"]),
            ("user", prompt_data["user"])
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({})
        
        # The response should contain a list of tickers and reasons.
        # In a real implementation, we might use a tool to search Google/Bing first.
        # For now, we rely on the LLM's internal knowledge or we could add a search tool.
        
        return {
            "scout_report": response.content,
            "opportunities": [] # To be parsed or structured
        }
    
    return scout_agent_node
