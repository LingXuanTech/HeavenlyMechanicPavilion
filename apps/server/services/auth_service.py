"""用户认证服务 - JWT 令牌管理、密码哈希、用户操作"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from config.settings import settings
from db.models import User, RefreshToken

logger = structlog.get_logger()

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============ 密码工具 ============

def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


# ============ JWT 令牌工具 ============

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 Access Token

    Args:
        user_id: 用户 ID
        expires_delta: 自定义过期时间，默认使用配置

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int, session: Session) -> str:
    """
    创建 Refresh Token 并存入数据库

    Args:
        user_id: 用户 ID
        session: 数据库会话

    Returns:
        Refresh token string
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    session.add(refresh_token)
    session.commit()

    return token


def verify_access_token(token: str) -> Optional[int]:
    """
    验证 Access Token

    Args:
        token: JWT token string

    Returns:
        用户 ID，验证失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except JWTError as e:
        logger.debug("JWT verification failed", error=str(e))
        return None


def verify_refresh_token(token: str, session: Session) -> Optional[RefreshToken]:
    """
    验证 Refresh Token

    Args:
        token: Refresh token string
        session: 数据库会话

    Returns:
        RefreshToken 对象，验证失败返回 None
    """
    statement = select(RefreshToken).where(
        RefreshToken.token == token,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    )
    return session.exec(statement).first()


def revoke_refresh_token(token: str, session: Session) -> bool:
    """
    撤销 Refresh Token

    Args:
        token: Refresh token string
        session: 数据库会话

    Returns:
        是否成功撤销
    """
    statement = select(RefreshToken).where(RefreshToken.token == token)
    refresh_token = session.exec(statement).first()

    if refresh_token:
        refresh_token.revoked = True
        session.add(refresh_token)
        session.commit()
        return True
    return False


def revoke_all_user_tokens(user_id: int, session: Session) -> int:
    """
    撤销用户所有 Refresh Token（用于密码重置、账号安全场景）

    Args:
        user_id: 用户 ID
        session: 数据库会话

    Returns:
        撤销的令牌数量
    """
    statement = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    )
    tokens = session.exec(statement).all()

    for token in tokens:
        token.revoked = True
        session.add(token)

    session.commit()
    return len(tokens)


# ============ 用户操作 ============

def get_user_by_email(email: str, session: Session) -> Optional[User]:
    """通过邮箱获取用户"""
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_user_by_id(user_id: int, session: Session) -> Optional[User]:
    """通过 ID 获取用户"""
    return session.get(User, user_id)


def create_user(
    email: str,
    password: Optional[str] = None,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    session: Session = None
) -> User:
    """
    创建新用户

    Args:
        email: 用户邮箱
        password: 密码（可选，OAuth 用户可无密码）
        display_name: 显示名称
        avatar_url: 头像 URL
        session: 数据库会话

    Returns:
        新创建的 User 对象
    """
    user = User(
        email=email,
        hashed_password=hash_password(password) if password else None,
        display_name=display_name or email.split("@")[0],
        avatar_url=avatar_url
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info("User created", user_id=user.id, email=email)
    return user


def authenticate_user(email: str, password: str, session: Session) -> Optional[User]:
    """
    验证用户凭证

    Args:
        email: 用户邮箱
        password: 密码
        session: 数据库会话

    Returns:
        验证成功返回 User 对象，否则返回 None
    """
    user = get_user_by_email(email, session)

    if not user:
        logger.debug("User not found", email=email)
        return None

    if not user.hashed_password:
        logger.debug("User has no password (OAuth only)", email=email)
        return None

    if not verify_password(password, user.hashed_password):
        logger.debug("Password verification failed", email=email)
        return None

    if not user.is_active:
        logger.debug("User is inactive", email=email)
        return None

    return user


def update_user_password(user: User, new_password: str, session: Session) -> None:
    """更新用户密码"""
    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.now()
    session.add(user)
    session.commit()

    # 撤销所有现有 refresh token
    revoke_all_user_tokens(user.id, session)
    logger.info("Password updated, all tokens revoked", user_id=user.id)
