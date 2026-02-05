"""
AI 配置 API 路由

提供 AI 提供商和模型配置的 REST API：
- 提供商 CRUD
- 模型配置管理
- 连接测试
- 配置刷新
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Any, Dict
import structlog

from services.ai_config_service import ai_config_service
from api.schemas.ai_config import (
    AIProvider,
    AIModelConfig,
    AIConfigStatus,
    TestProviderResult,
    ProviderListResponse,
    ModelConfigListResponse,
    ProviderCreateRequest,
    ProviderUpdateRequest,
    ModelConfigUpdateRequest
)

router = APIRouter(prefix="/ai", tags=["AI Configuration"])
logger = structlog.get_logger()


# ============ 提供商 API ============

@router.get("/providers", response_model=ProviderListResponse)
async def list_providers():
    """列出所有 AI 提供商"""
    try:
        providers = await ai_config_service.list_providers()
        return {"providers": providers}
    except Exception as e:
        logger.error("Failed to list providers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider_id}", response_model=AIProvider)
async def get_provider(provider_id: int):
    """获取单个提供商详情"""
    provider = await ai_config_service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/providers")
async def create_provider(data: ProviderCreateRequest):
    """创建新提供商"""
    try:
        result = await ai_config_service.create_provider(data.model_dump())
        return result
    except Exception as e:
        logger.error("Failed to create provider", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: int, data: ProviderUpdateRequest):
    """更新提供商"""
    # 过滤掉 None 值
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    result = await ai_config_service.update_provider(provider_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Provider not found")
    return result


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int):
    """删除提供商"""
    success = await ai_config_service.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"deleted": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: int):
    """测试提供商连接"""
    result = await ai_config_service.test_provider(provider_id)
    return result


# ============ 模型配置 API ============

@router.get("/models")
async def get_model_configs():
    """获取所有模型配置"""
    configs = await ai_config_service.get_model_configs()
    return {"configs": configs}


@router.get("/models", response_model=ModelConfigListResponse)
async def list_model_configs():
    """列出所有模型配置"""
    try:
        configs = await ai_config_service.get_model_configs()
        return {"configs": configs}
    except Exception as e:
        logger.error("Failed to list model configs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/models/{config_key}")
async def update_model_config(config_key: str, data: ModelConfigUpdateRequest):
    """更新模型配置"""
    result = await ai_config_service.update_model_config(
        config_key=config_key,
        provider_id=data.provider_id,
        model_name=data.model_name,
    )
    return result


@router.post("/providers/{provider_id}/test", response_model=TestProviderResult)
async def test_provider(provider_id: int):
    """测试提供商连接"""
    try:
        result = await ai_config_service.test_provider(provider_id)
        return result
    except Exception as e:
        logger.error("Failed to test provider", provider_id=provider_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ 管理 API ============

@router.post("/refresh")
async def refresh_config():
    """强制刷新配置缓存"""
    ai_config_service.refresh_config()
    return {"refreshed": True}


@router.get("/status", response_model=AIConfigStatus)
async def get_status():
    """获取 AI 配置服务状态"""
    return ai_config_service.get_status()
