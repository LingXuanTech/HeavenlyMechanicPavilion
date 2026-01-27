"""设置管理 API 路由"""
import yaml
import structlog
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from pydantic import BaseModel

from config.settings import settings
from services.prompt_manager import prompt_manager
from api.dependencies import verify_api_key

router = APIRouter(prefix="/settings", tags=["Settings"])
logger = structlog.get_logger()


class PromptConfig(BaseModel):
    """单个角色的 Prompt 配置"""
    system: str
    user: str


class PromptsUpdateRequest(BaseModel):
    """Prompt 更新请求"""
    prompts: Dict[str, PromptConfig]


@router.get("/prompts")
async def get_all_prompts():
    """获取所有 Agent Prompt 配置"""
    prompt_manager._load_prompts()  # 确保获取最新
    return {
        "prompts": prompt_manager._prompts,
        "path": settings.PROMPTS_YAML_PATH
    }


@router.get("/prompts/{role}")
async def get_prompt_by_role(role: str):
    """获取特定 Agent 的 Prompt 配置"""
    prompt_manager._load_prompts()
    prompt_config = prompt_manager._prompts.get(role)

    if not prompt_config:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt for role '{role}' not found. Available roles: {list(prompt_manager._prompts.keys())}"
        )

    return {
        "role": role,
        "config": prompt_config
    }


@router.put("/prompts", dependencies=[Depends(verify_api_key)])
async def update_prompts(request: PromptsUpdateRequest):
    """
    更新所有 Prompt 配置

    需要 API Key 认证。
    """
    try:
        # 转换为可序列化的字典
        prompts_dict = {
            role: {"system": config.system, "user": config.user}
            for role, config in request.prompts.items()
        }

        # 写入 YAML 文件
        with open(settings.PROMPTS_YAML_PATH, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                prompts_dict,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )

        # 强制重新加载
        prompt_manager._last_mtime = 0
        prompt_manager._load_prompts()

        logger.info("Prompts updated successfully")

        return {
            "status": "success",
            "message": "Prompts updated successfully",
            "roles_updated": list(request.prompts.keys())
        }

    except Exception as e:
        logger.error("Failed to update prompts", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update prompts: {str(e)}")


@router.put("/prompts/{role}", dependencies=[Depends(verify_api_key)])
async def update_single_prompt(role: str, config: PromptConfig):
    """
    更新单个角色的 Prompt 配置

    需要 API Key 认证。
    """
    try:
        # 加载现有配置
        prompt_manager._load_prompts()
        current_prompts = prompt_manager._prompts.copy()

        # 更新指定角色
        current_prompts[role] = {
            "system": config.system,
            "user": config.user
        }

        # 写入 YAML 文件
        with open(settings.PROMPTS_YAML_PATH, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                current_prompts,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )

        # 强制重新加载
        prompt_manager._last_mtime = 0
        prompt_manager._load_prompts()

        logger.info("Single prompt updated successfully", role=role)

        return {
            "status": "success",
            "message": f"Prompt for role '{role}' updated successfully",
            "role": role
        }

    except Exception as e:
        logger.error("Failed to update single prompt", role=role, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {str(e)}")


@router.post("/prompts/reload")
async def reload_prompts():
    """强制重新加载 Prompt 配置（不需要认证）"""
    prompt_manager._last_mtime = 0
    prompt_manager._load_prompts()

    return {
        "status": "success",
        "message": "Prompts reloaded from file",
        "roles": list(prompt_manager._prompts.keys())
    }
