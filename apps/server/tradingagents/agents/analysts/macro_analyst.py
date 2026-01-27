from langchain_core.prompts import ChatPromptTemplate
from services.prompt_manager import prompt_manager
import structlog

logger = structlog.get_logger()

def create_macro_analyst(llm):
    async def macro_analyst_node(state):
        symbol = state.get("company_of_interest", "Unknown")
        logger.info("Macro analyst analyzing", symbol=symbol)
        
        prompt_data = prompt_manager.get_prompt("macro_analyst", {"symbol": symbol})
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system"]),
            ("user", "请开始分析。")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({})
        
        return {
            "macro_report": response.content
        }
    
    return macro_analyst_node
