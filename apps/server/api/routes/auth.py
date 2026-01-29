"""用户认证路由 - 邮箱/密码登录注册"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session
from typing import Optional

from db.models import get_session, User
from services.auth_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
)
from api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = structlog.get_logger()


# ============ 请求/响应模型 ============

class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="密码至少 8 位")
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    email_verified: bool
    created_at: str

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            email_verified=user.email_verified,
            created_at=user.created_at.isoformat()
        )


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


# ============ 路由端点 ============

@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    response: Response,
    session: Session = Depends(get_session)
):
    """
    注册新用户

    - 邮箱必须唯一
    - 密码至少 8 位
    - 自动创建 access_token 和 refresh_token
    """
    # 检查邮箱是否已注册
    existing = get_user_by_email(request.email, session)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 创建用户
    user = create_user(
        email=request.email,
        password=request.password,
        display_name=request.display_name,
        session=session
    )

    # 生成令牌
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id, session)

    # 设置 refresh_token 到 HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # 生产环境应设为 True
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 天
    )

    # 返回响应头中包含 access_token
    response.headers["X-Access-Token"] = access_token

    logger.info("User registered", user_id=user.id, email=user.email)
    return UserResponse.from_user(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: Session = Depends(get_session)
):
    """
    用户登录

    - 验证邮箱和密码
    - 返回 access_token，refresh_token 存入 HttpOnly cookie
    """
    user = authenticate_user(request.email, request.password, session)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # 生成令牌
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id, session)

    # 设置 refresh_token 到 HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # 生产环境应设为 True
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    logger.info("User logged in", user_id=user.id, email=user.email)

    from config.settings import settings
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    用户登出

    - 撤销 refresh_token
    - 清除 cookie
    """
    # 从请求体或 cookie 获取 refresh_token
    # 注意：实际应从 cookie 读取
    if refresh_token:
        revoke_refresh_token(refresh_token, session)

    # 清除 cookie
    response.delete_cookie(key="refresh_token")

    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    response: Response,
    session: Session = Depends(get_session)
):
    """
    刷新 access_token

    - 验证 refresh_token
    - 生成新的 access_token
    """
    token_record = verify_refresh_token(request.refresh_token, session)

    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # 生成新的 access_token
    access_token = create_access_token(token_record.user_id)

    from config.settings import settings
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息

    - 需要有效的 access_token
    """
    return UserResponse.from_user(current_user)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    更新用户资料
    """
    if display_name is not None:
        current_user.display_name = display_name
    if avatar_url is not None:
        current_user.avatar_url = avatar_url

    from datetime import datetime
    current_user.updated_at = datetime.now()
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return UserResponse.from_user(current_user)
