"""API 依赖注入模块"""
import structlog
from fastapi import Header, HTTPException, Depends
from typing import Optional

from config.settings import settings

logger = structlog.get_logger()


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> bool:
    """
    验证 API Key 的依赖函数。

    当 API_KEY_ENABLED=true 时，要求请求头中包含有效的 X-API-Key。
    当 API_KEY_ENABLED=false 时，跳过验证。
    """
    if not settings.API_KEY_ENABLED:
        return True

    if not x_api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=401,
            detail="API key required. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    if x_api_key != settings.API_KEY:
        logger.warning("Invalid API key provided")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return True


async def optional_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> Optional[str]:
    """
    可选的 API Key 验证。

    用于某些端点需要区分认证用户和匿名用户的场景。
    """
    if not x_api_key:
        return None

    if x_api_key == settings.API_KEY:
        return x_api_key

    return None


# 依赖别名，便于在路由中使用
RequireApiKey = Depends(verify_api_key)
OptionalApiKey = Depends(optional_api_key)
