import asyncio
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from db.models import ChatHistory, get_session
from config.settings import settings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = structlog.get_logger()


def _create_llm():
    """延迟创建 LLM 实例，优雅处理 API key 缺失"""
    if settings.GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.GOOGLE_API_KEY)
    elif settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
    else:
        logger.warning("No LLM API key configured (OPENAI_API_KEY or GOOGLE_API_KEY)")
        return None


class ChatService:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        """延迟初始化 LLM"""
        if self._llm is None:
            self._llm = _create_llm()
        return self._llm

    async def get_response(self, thread_id: str, message: str, history: List[ChatHistory]) -> str:
        if self.llm is None:
            raise HTTPException(status_code=503, detail="Chat service unavailable: No LLM API key configured")

        messages = [
            SystemMessage(content="你是一个专业的投资顾问助手。请基于历史对话和当前问题提供专业的建议。")
        ]

        for h in history:
            if h.role == "user":
                messages.append(HumanMessage(content=h.content))
            else:
                messages.append(AIMessage(content=h.content))

        messages.append(HumanMessage(content=message))

        response = await self.llm.ainvoke(messages)
        return response.content

chat_service = ChatService()

from api.schemas.chat import ChatMessage, ChatResponse

@router.get("/{thread_id}", response_model=List[ChatMessage])
async def get_chat_history(thread_id: str, session: Session = Depends(get_session)):
    statement = select(ChatHistory).where(ChatHistory.thread_id == thread_id).order_by(ChatHistory.created_at)
    results = session.exec(statement).all()
    return [ChatMessage(role=r.role, content=r.content, timestamp=r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at)) for r in results]

@router.post("/{thread_id}", response_model=ChatMessage)
async def send_message(thread_id: str, message: str, session: Session = Depends(get_session)):
    # Get history
    statement = select(ChatHistory).where(ChatHistory.thread_id == thread_id).order_by(ChatHistory.created_at)
    history = session.exec(statement).all()
    
    # Save user message
    user_msg = ChatHistory(thread_id=thread_id, role="user", content=message)
    session.add(user_msg)
    
    # Get AI response
    try:
        ai_content = await chat_service.get_response(thread_id, message, history)
        ai_msg = ChatHistory(thread_id=thread_id, role="assistant", content=ai_content)
        session.add(ai_msg)
        session.commit()
        
        return {"role": "assistant", "content": ai_content}
    except Exception as e:
        logger.error("Chat failed", error=str(e))
        raise HTTPException(status_code=500, detail="Chat service unavailable")
