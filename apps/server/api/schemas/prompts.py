"""Prompt 相关的 Pydantic Schema 定义"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from db.models import AgentCategory


class PromptUpdateRequest(BaseModel):
    """Prompt 更新请求"""
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    available_variables: Optional[List[str]] = None
    change_note: Optional[str] = None


class PromptRollbackRequest(BaseModel):
    """Prompt 回滚请求"""
    target_version: int


class YamlImportRequest(BaseModel):
    """YAML 导入请求"""
    yaml_content: str


class PromptVersionInfo(BaseModel):
    """Prompt 版本信息"""
    id: int
    prompt_id: int
    version: int
    system_prompt: str
    user_prompt_template: str
    change_note: Optional[str] = None
    created_at: datetime


class AgentPromptInfo(BaseModel):
    """Agent Prompt 基础信息"""
    id: int
    agent_key: str
    category: AgentCategory
    display_name: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt_template: str
    current_version: int
    available_variables: List[str] = Field(default_factory=list)
    updated_at: datetime


class AgentPromptDetail(AgentPromptInfo):
    """Agent Prompt 详细信息，包含版本历史和变量映射"""
    version_history: List[PromptVersionInfo] = Field(default_factory=list)
    variable_mapping: Dict[str, Any] = Field(default_factory=dict)


class PromptListResponse(BaseModel):
    """Prompt 列表响应"""
    prompts: List[AgentPromptInfo]
    total: int


class PromptServiceStatus(BaseModel):
    """Prompt 服务状态"""
    is_initialized: bool
    total_prompts: int
    categories: List[str]
    last_reload: Optional[datetime] = None
