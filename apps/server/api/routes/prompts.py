"""
Prompt 配置 API 路由

提供 Agent Prompt 的 CRUD 操作和 YAML 导入导出
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

from services.prompt_config_service import prompt_config_service
from db.models import AgentCategory

router = APIRouter(prefix="/prompts", tags=["Prompt Config"])


# ============ Pydantic Models ============

class PromptUpdateRequest(BaseModel):
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    available_variables: Optional[List[str]] = None
    change_note: Optional[str] = None


class PromptRollbackRequest(BaseModel):
    target_version: int


class YamlImportRequest(BaseModel):
    yaml_content: str


# ============ 路由 ============

@router.get("/")
async def list_prompts(
    category: Optional[str] = Query(None, description="Filter by category: analyst, researcher, manager, risk, trader, synthesizer")
):
    """
    列出所有 Agent Prompt

    可选按类别过滤
    """
    cat = None
    if category:
        try:
            cat = AgentCategory(category)
        except ValueError:
            raise HTTPException(400, f"Invalid category: {category}")

    prompts = await prompt_config_service.list_prompts(cat)
    return {
        "prompts": prompts,
        "total": len(prompts),
    }


@router.get("/categories")
async def list_categories():
    """列出所有 Agent 类别"""
    return {
        "categories": [
            {"value": c.value, "label": c.name.title()}
            for c in AgentCategory
        ]
    }


@router.get("/status")
async def get_service_status():
    """获取 Prompt 配置服务状态"""
    return prompt_config_service.get_status()


@router.get("/{prompt_id}")
async def get_prompt_detail(prompt_id: int):
    """
    获取单个 Prompt 详情

    包含版本历史
    """
    detail = await prompt_config_service.get_prompt_detail(prompt_id)
    if not detail:
        raise HTTPException(404, "Prompt not found")
    return detail


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: int, request: PromptUpdateRequest):
    """
    更新 Prompt

    自动保存版本历史，支持回滚
    """
    data = request.model_dump(exclude_none=True, exclude={"change_note"})
    if not data:
        raise HTTPException(400, "No fields to update")

    result = await prompt_config_service.update_prompt(
        prompt_id,
        data,
        change_note=request.change_note or "",
        created_by="api",
    )

    if not result:
        raise HTTPException(404, "Prompt not found")

    return result


@router.post("/{prompt_id}/rollback")
async def rollback_prompt(prompt_id: int, request: PromptRollbackRequest):
    """
    回滚 Prompt 到指定版本
    """
    result = await prompt_config_service.rollback_prompt(
        prompt_id,
        request.target_version,
    )

    if not result:
        raise HTTPException(404, "Prompt not found")

    if "error" in result:
        raise HTTPException(400, result["error"])

    return result


@router.post("/refresh")
async def refresh_cache():
    """强制刷新 Prompt 缓存"""
    prompt_config_service.refresh_cache()
    return {"status": "refreshed", **prompt_config_service.get_status()}


# ============ YAML 导入导出 ============

@router.get("/export/yaml", response_class=PlainTextResponse)
async def export_yaml():
    """
    导出所有 Prompt 到 YAML 格式

    可用于备份或在版本控制中跟踪变更
    """
    yaml_content = await prompt_config_service.export_to_yaml()
    return PlainTextResponse(
        content=yaml_content,
        media_type="text/yaml",
        headers={
            "Content-Disposition": "attachment; filename=agent_prompts.yaml"
        }
    )


@router.post("/import/yaml")
async def import_yaml(request: YamlImportRequest):
    """
    从 YAML 导入 Prompt

    - 已存在的 agent_key 会被更新（并保存版本历史）
    - 新的 agent_key 会被创建
    """
    result = await prompt_config_service.import_from_yaml(
        request.yaml_content,
        created_by="yaml_import",
    )

    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Import failed"))

    return result


# ============ 便捷查询 ============

@router.get("/by-key/{agent_key}")
async def get_prompt_by_key(agent_key: str):
    """
    根据 agent_key 获取 Prompt

    这是 Agent 代码使用的主要接口
    """
    prompt = prompt_config_service.get_prompt(agent_key)
    if not prompt.get("system"):
        raise HTTPException(404, f"Prompt not found for agent: {agent_key}")

    return {
        "agent_key": agent_key,
        "system_prompt": prompt["system"],
        "user_prompt_template": prompt["user"],
    }


@router.post("/preview")
async def preview_prompt(
    agent_key: str = Query(..., description="Agent key"),
    variables: Dict[str, Any] = None
):
    """
    预览 Prompt（带变量注入）

    用于测试 Prompt 模板效果
    """
    prompt = prompt_config_service.get_prompt(agent_key, variables or {})
    if not prompt.get("system"):
        raise HTTPException(404, f"Prompt not found for agent: {agent_key}")

    return {
        "agent_key": agent_key,
        "rendered_system_prompt": prompt["system"],
        "rendered_user_prompt": prompt["user"],
        "variables_used": variables or {},
    }
