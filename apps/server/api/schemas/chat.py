"""Chat 相关的 Pydantic Schema 定义"""

from typing import List, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息"""
    role: Literal["user", "assistant", "system"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")


class ChatResponse(BaseModel):
    """聊天响应"""
    messages: List[ChatMessage] = Field(..., description="消息列表")
    thread_id: str = Field(..., description="会话 ID")
