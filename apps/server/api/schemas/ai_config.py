"""AI 配置相关的 Pydantic Schema 定义"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from db.models import AIProviderType


class AIProvider(BaseModel):
    """AI 提供商信息"""
    id: int
    name: str
    provider_type: AIProviderType
    base_url: Optional[str] = None
    api_key_masked: str
    models: List[str]
    is_enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime


class AIModelConfig(BaseModel):
    """AI 模型配置"""
    config_key: str
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    model_name: str
    is_active: bool
    updated_at: datetime


class AIConfigStatus(BaseModel):
    """AI 配置状态"""
    initialized: bool
    providers_count: int
    configs_count: int
    cached_llms: List[str]
    last_refresh: Optional[datetime] = None


class TestProviderResult(BaseModel):
    """测试提供商结果"""
    success: bool
    model: Optional[str] = None
    response_preview: Optional[str] = None
    error: Optional[str] = None


class ProviderListResponse(BaseModel):
    """提供商列表响应"""
    providers: List[AIProvider]


class ModelConfigListResponse(BaseModel):
    """模型配置列表响应"""
    configs: List[AIModelConfig]


class ProviderCreateRequest(BaseModel):
    """创建提供商请求"""
    name: str
    provider_type: AIProviderType
    base_url: Optional[str] = None
    api_key: str = ""
    models: List[str] = []
    is_enabled: bool = True
    priority: int = 99


class ProviderUpdateRequest(BaseModel):
    """更新提供商请求"""
    name: Optional[str] = None
    provider_type: Optional[AIProviderType] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[List[str]] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


class ModelConfigUpdateRequest(BaseModel):
    """更新模型配置请求"""
    provider_id: int
    model_name: str
