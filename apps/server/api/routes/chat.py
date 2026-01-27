import asyncio
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any
from db.models import ChatHistory, get_session
from config.settings import settings
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = structlog.get_logger()

class ChatService:
    def __init__(self):
        if settings.GOOGLE_API_KEY:
            self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.GOOGLE_API_KEY)
        else:
            self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)

    async def get_response(self, thread_id: str, message: str, history: List[ChatHistory]) -> str:
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

@router.get("/{thread_id}", response_model=List[Dict[str, Any]])
async def get_chat_history(thread_id: str, session: Session = Depends(get_session)):
    statement = select(ChatHistory).where(ChatHistory.thread_id == thread_id).order_by(ChatHistory.created_at)
    results = session.exec(statement).all()
    return [{"role": r.role, "content": r.content, "timestamp": r.created_at} for r in results]

@router.post("/{thread_id}")
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
