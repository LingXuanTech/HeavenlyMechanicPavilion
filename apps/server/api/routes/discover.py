import asyncio
import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List, Dict, Any
from services.prompt_manager import prompt_manager
from services.ai_config_service import ai_config_service
from langchain_core.prompts import ChatPromptTemplate
import json

router = APIRouter(prefix="/discover", tags=["Discovery"])
logger = structlog.get_logger()

class DiscoveryService:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        """通过 ai_config_service 统一获取 LLM"""
        return ai_config_service.get_llm("quick_think")

    async def discover_stocks(self, query: str) -> List[Dict[str, Any]]:
        logger.info("Discovering stocks", query=query)
        
        prompt_data = prompt_manager.get_prompt("scout_agent", {"query": query})
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system"] + "\n请输出严格的 JSON 数组格式，每个对象包含 symbol, name, reason, confidence (0-100)。不要包含 Markdown 代码块。"),
            ("user", prompt_data["user"])
        ])
        
        chain = prompt | self.llm
        response = await chain.ainvoke({})
        content = response.content.strip()
        
        # Clean up potential markdown blocks
        if content.startswith("```json"):
            content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
        elif content.startswith("```"):
            content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
        content = content.strip()
        
        try:
            return json.loads(content)
        except Exception as e:
            logger.error("Failed to parse discovery JSON", error=str(e), content=content)
            return []

discovery_service = DiscoveryService()

@router.get("/")
async def discover(query: str):
    """
    Discover potential stocks based on a query or intent.
    """
    results = await discovery_service.discover_stocks(query)
    return {"query": query, "results": results}
