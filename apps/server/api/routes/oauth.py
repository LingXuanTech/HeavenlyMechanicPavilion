"""OAuth 2.0 认证路由"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from typing import Optional

from db.models import get_session, User, OAuthAccount
from services.auth_service import (
    create_user,
    get_user_by_email,
    create_access_token,
    create_refresh_token,
)
from config.oauth import oauth, get_enabled_providers
from config.settings import settings
from api.dependencies import get_current_user

router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])
logger = structlog.get_logger()


@router.get("/providers")
async def list_providers():
    """
    获取已启用的 OAuth 提供商列表
    """
    return {"providers": get_enabled_providers()}


@router.get("/{provider}")
async def oauth_login(provider: str, request: Request):
    """
    发起 OAuth 登录

    重定向到第三方授权页面
    """
    if provider not in get_enabled_providers():
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' is not configured")

    client = oauth.create_client(provider)
    redirect_uri = f"{settings.WEBAUTHN_ORIGIN}/api/auth/oauth/{provider}/callback"

    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    """
    OAuth 回调处理

    - 获取用户信息
    - 关联或创建用户
    - 生成令牌
    """
    if provider not in get_enabled_providers():
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' is not configured")

    try:
        client = oauth.create_client(provider)
        token = await client.authorize_access_token(request)
    except Exception as e:
        logger.error("OAuth token exchange failed", provider=provider, error=str(e))
        raise HTTPException(status_code=400, detail="OAuth authorization failed")

    # 获取用户信息
    user_info = await _get_user_info(client, provider, token)

    if not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Email not available from OAuth provider")

    # 查找或创建用户
    user = await _find_or_create_user(
        provider=provider,
        provider_user_id=user_info["id"],
        email=user_info["email"],
        display_name=user_info.get("name"),
        avatar_url=user_info.get("avatar_url"),
        access_token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        session=session
    )

    # 生成令牌
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id, session)

    # 设置 cookie 并重定向到前端
    redirect_url = f"{settings.WEBAUTHN_ORIGIN}/?token={access_token}"

    resp = RedirectResponse(url=redirect_url)
    resp.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # 生产环境设为 True
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    logger.info("OAuth login successful", provider=provider, user_id=user.id)
    return resp


@router.delete("/{provider}")
async def unlink_oauth(
    provider: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    解绑 OAuth 账号

    - 用户必须有密码或其他登录方式
    """
    # 检查用户是否有密码
    if not current_user.hashed_password:
        # 检查是否有其他 OAuth 账号
        statement = select(OAuthAccount).where(
            OAuthAccount.user_id == current_user.id,
            OAuthAccount.provider != provider
        )
        other_accounts = session.exec(statement).all()

        if not other_accounts:
            raise HTTPException(
                status_code=400,
                detail="Cannot unlink: this is your only login method. Set a password first."
            )

    # 删除 OAuth 关联
    statement = select(OAuthAccount).where(
        OAuthAccount.user_id == current_user.id,
        OAuthAccount.provider == provider
    )
    oauth_account = session.exec(statement).first()

    if not oauth_account:
        raise HTTPException(status_code=404, detail=f"OAuth account for '{provider}' not found")

    session.delete(oauth_account)
    session.commit()

    logger.info("OAuth account unlinked", provider=provider, user_id=current_user.id)
    return {"message": f"Successfully unlinked {provider} account"}


@router.get("/accounts")
async def list_oauth_accounts(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    列出用户关联的 OAuth 账号
    """
    statement = select(OAuthAccount).where(OAuthAccount.user_id == current_user.id)
    accounts = session.exec(statement).all()

    return {
        "accounts": [
            {
                "provider": acc.provider,
                "created_at": acc.created_at.isoformat()
            }
            for acc in accounts
        ]
    }


# ============ 辅助函数 ============

async def _get_user_info(client, provider: str, token: dict) -> dict:
    """从 OAuth 提供商获取用户信息"""

    if provider == "google":
        # Google 使用 OpenID Connect
        user_info = token.get("userinfo", {})
        return {
            "id": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "avatar_url": user_info.get("picture"),
        }

    elif provider == "github":
        # GitHub 需要额外请求用户信息
        resp = await client.get("user", token=token)
        user_data = resp.json()

        # GitHub 邮箱可能是私有的，需要单独获取
        email = user_data.get("email")
        if not email:
            email_resp = await client.get("user/emails", token=token)
            emails = email_resp.json()
            primary_email = next((e for e in emails if e.get("primary")), None)
            email = primary_email["email"] if primary_email else None

        return {
            "id": str(user_data.get("id")),
            "email": email,
            "name": user_data.get("name") or user_data.get("login"),
            "avatar_url": user_data.get("avatar_url"),
        }

    return {}


async def _find_or_create_user(
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: Optional[str],
    avatar_url: Optional[str],
    access_token: Optional[str],
    refresh_token: Optional[str],
    session: Session
) -> User:
    """查找或创建用户，并关联 OAuth 账号"""

    # 先查找已有的 OAuth 关联
    statement = select(OAuthAccount).where(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id
    )
    oauth_account = session.exec(statement).first()

    if oauth_account:
        # 已有关联，更新 token
        oauth_account.access_token = access_token
        oauth_account.refresh_token = refresh_token
        session.add(oauth_account)
        session.commit()

        return session.get(User, oauth_account.user_id)

    # 查找同邮箱用户
    user = get_user_by_email(email, session)

    if not user:
        # 创建新用户
        user = create_user(
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            session=session
        )
        user.email_verified = True  # OAuth 登录视为已验证
        session.add(user)
        session.commit()

    # 创建 OAuth 关联
    oauth_account = OAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        access_token=access_token,
        refresh_token=refresh_token
    )
    session.add(oauth_account)
    session.commit()

    return user
