import asyncio
import re
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from db.models import ChatHistory, AnalysisResult, Watchlist, get_session
from config.settings import settings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from services.prompt_manager import prompt_manager

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


def _build_context(session: Session, message: str) -> str:
    """构建 Fund Manager 上下文信息

    包含用户自选股列表和最近分析结果，以及 @symbol 引用的股票数据。

    Args:
        session: 数据库会话
        message: 用户消息（用于提取 @symbol 引用）

    Returns:
        格式化的上下文字符串
    """
    context_parts = []

    # 1. 获取用户自选股列表
    try:
        watchlist = session.exec(select(Watchlist)).all()
        if watchlist:
            symbols = [w.symbol for w in watchlist]
            context_parts.append(f"用户自选股: {', '.join(symbols)}")
    except Exception as e:
        logger.debug("Failed to load watchlist for chat context", error=str(e))

    # 2. 提取 @symbol 引用并获取对应分析数据
    mentioned_symbols = re.findall(r'@([A-Za-z0-9.]+)', message)

    # 3. 获取最近的分析结果（自选股 + @引用的股票）
    target_symbols = set(mentioned_symbols)
    try:
        if watchlist:
            # 添加自选股中最近分析过的
            for w in watchlist[:5]:  # 限制数量避免上下文过长
                target_symbols.add(w.symbol)
    except Exception:
        pass

    for symbol in target_symbols:
        try:
            stmt = (
                select(AnalysisResult)
                .where(AnalysisResult.symbol == symbol, AnalysisResult.status == "completed")
                .order_by(AnalysisResult.created_at.desc())
                .limit(1)
            )
            result = session.exec(stmt).first()
            if result and result.result_json:
                import json
                data = json.loads(result.result_json) if isinstance(result.result_json, str) else result.result_json
                signal = data.get("signal", "N/A")
                confidence = data.get("confidence", "N/A")
                reasoning = data.get("reasoning", "")[:200]
                context_parts.append(
                    f"\n📊 {symbol} 最近分析 ({result.created_at.strftime('%Y-%m-%d %H:%M') if result.created_at else 'N/A'}):\n"
                    f"  信号: {signal} | 信心度: {confidence}\n"
                    f"  摘要: {reasoning}"
                )
        except Exception as e:
            logger.debug("Failed to load analysis for chat context", symbol=symbol, error=str(e))

    if not context_parts:
        return "暂无自选股和分析数据。"

    return "\n".join(context_parts)


def _get_system_prompt(context: str) -> str:
    """获取 Fund Manager 系统 prompt

    优先从 prompts.yaml 加载，失败时使用默认 prompt。

    Args:
        context: 上下文信息字符串

    Returns:
        完整的系统 prompt
    """
    try:
        prompt_data = prompt_manager.get_prompt("fund_manager_chat", {"context": context, "message": ""})
        if prompt_data and prompt_data.get("system"):
            return prompt_data["system"]
    except Exception as e:
        logger.debug("Using default fund manager chat prompt", reason=str(e))

    # 默认 prompt（prompts.yaml 不可用时的降级）
    return (
        "你是一位经验丰富的基金经理（Fund Manager），拥有 15 年以上的投资管理经验。\n"
        "你管理着一只多策略基金，覆盖 A股、港股和美股市场。\n\n"
        "请基于以下上下文信息和历史对话，提供专业的投资建议。\n"
        "观点要明确，给出具体的操作建议，始终附带风险提示。\n\n"
        f"## 上下文信息\n\n{context}\n\n"
        "输出语言：简体中文。"
    )


class ChatService:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        """延迟初始化 LLM"""
        if self._llm is None:
            self._llm = _create_llm()
        return self._llm

    async def get_response(
        self,
        thread_id: str,
        message: str,
        history: List[ChatHistory],
        session: Optional[Session] = None,
    ) -> str:
        """生成 AI 回复

        Args:
            thread_id: 对话线程 ID
            message: 用户消息
            history: 历史对话记录
            session: 数据库会话（用于加载上下文）

        Returns:
            AI 回复内容
        """
        if self.llm is None:
            raise HTTPException(status_code=503, detail="Chat service unavailable: No LLM API key configured")

        # 构建 Fund Manager 上下文
        context = ""
        if session:
            try:
                context = _build_context(session, message)
            except Exception as e:
                logger.warning("Failed to build chat context", error=str(e))
                context = "上下文加载失败。"

        system_prompt = _get_system_prompt(context)

        messages = [SystemMessage(content=system_prompt)]

        # 限制历史消息数量避免上下文过长
        recent_history = history[-20:] if len(history) > 20 else history
        for h in recent_history:
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
        ai_content = await chat_service.get_response(thread_id, message, history, session=session)
        ai_msg = ChatHistory(thread_id=thread_id, role="assistant", content=ai_content)
        session.add(ai_msg)
        session.commit()
        
        return {"role": "assistant", "content": ai_content}
    except Exception as e:
        logger.error("Chat failed", error=str(e))
        raise HTTPException(status_code=500, detail="Chat service unavailable")
