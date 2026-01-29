"""API 依赖注入模块"""
import structlog
from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlmodel import Session

from config.settings import settings
from db.models import get_session, User

logger = structlog.get_logger()

# HTTP Bearer 认证方案
bearer_scheme = HTTPBearer(auto_error=False)


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


# ============ JWT 用户认证 ============

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    获取当前认证用户。

    从 Authorization: Bearer <token> 头中提取并验证 JWT，返回对应的 User 对象。
    """
    from services.auth_service import verify_access_token, get_user_by_id

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = verify_access_token(credentials.credentials)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = get_user_by_id(user_id, session)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is disabled"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: Session = Depends(get_session)
) -> Optional[User]:
    """
    可选的用户认证。

    如果提供了有效的 token 则返回用户，否则返回 None。
    用于某些端点需要区分认证用户和匿名用户的场景。
    """
    if not credentials:
        return None

    from services.auth_service import verify_access_token, get_user_by_id

    user_id = verify_access_token(credentials.credentials)
    if not user_id:
        return None

    user = get_user_by_id(user_id, session)
    if not user or not user.is_active:
        return None

    return user


# 依赖别名
RequireUser = Depends(get_current_user)
OptionalUser = Depends(get_current_user_optional)
