"""WebAuthn / Passkey 认证路由"""

import base64
import json
import structlog
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional, List

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import (
    bytes_to_base64url,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    PublicKeyCredentialDescriptor,
)

from db.models import get_session, User, WebAuthnCredential
from services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_user_by_email,
)
from config.settings import settings
from api.dependencies import get_current_user

router = APIRouter(prefix="/auth/passkey", tags=["Passkey"])
logger = structlog.get_logger()

# 临时存储挑战（生产环境应使用 Redis）
# 格式: {challenge_base64: {"user_id": int, "email": str, "expires": datetime}}
_challenges: dict = {}


# ============ 请求/响应模型 ============

class RegisterOptionsRequest(BaseModel):
    """获取注册选项请求（已登录用户添加 Passkey）"""
    device_name: Optional[str] = None


class RegisterOptionsResponse(BaseModel):
    """注册选项响应"""
    options: dict


class RegisterVerifyRequest(BaseModel):
    """验证注册响应"""
    credential: dict
    device_name: Optional[str] = None


class LoginOptionsRequest(BaseModel):
    """获取登录选项请求"""
    email: str


class LoginOptionsResponse(BaseModel):
    """登录选项响应"""
    options: dict


class LoginVerifyRequest(BaseModel):
    """验证登录响应"""
    email: str
    credential: dict


class CredentialResponse(BaseModel):
    """凭证信息响应"""
    id: int
    credential_id: str
    device_name: Optional[str]
    created_at: str
    last_used_at: Optional[str]


# ============ 注册流程 ============

@router.post("/register/options", response_model=RegisterOptionsResponse)
async def get_register_options(
    request: RegisterOptionsRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    获取 Passkey 注册选项（需要已登录）

    返回 WebAuthn 注册参数，前端使用 navigator.credentials.create() 创建凭证
    """
    # 获取已有凭证（排除重复注册）
    statement = select(WebAuthnCredential).where(
        WebAuthnCredential.user_id == current_user.id
    )
    existing_credentials = session.exec(statement).all()

    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in existing_credentials
    ]

    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=str(current_user.id).encode(),
        user_name=current_user.email,
        user_display_name=current_user.display_name or current_user.email,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    # 存储挑战
    challenge_b64 = bytes_to_base64url(options.challenge)
    _challenges[challenge_b64] = {
        "user_id": current_user.id,
        "device_name": request.device_name,
        "type": "registration",
    }

    return RegisterOptionsResponse(options=json.loads(options_to_json(options)))


@router.post("/register/verify")
async def verify_register(
    request: RegisterVerifyRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    验证 Passkey 注册响应

    验证成功后保存凭证到数据库
    """
    # 查找对应的挑战
    challenge_b64 = None
    challenge_data = None

    for ch, data in list(_challenges.items()):
        if data.get("user_id") == current_user.id and data.get("type") == "registration":
            challenge_b64 = ch
            challenge_data = data
            break

    if not challenge_data:
        raise HTTPException(status_code=400, detail="No pending registration challenge")

    try:
        verification = verify_registration_response(
            credential=request.credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
        )
    except Exception as e:
        logger.error("WebAuthn registration verification failed", error=str(e))
        del _challenges[challenge_b64]
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")

    # 保存凭证
    credential = WebAuthnCredential(
        user_id=current_user.id,
        credential_id=bytes_to_base64url(verification.credential_id),
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        device_name=request.device_name or challenge_data.get("device_name"),
    )
    session.add(credential)
    session.commit()

    # 清理挑战
    del _challenges[challenge_b64]

    logger.info("Passkey registered", user_id=current_user.id, credential_id=credential.credential_id[:20])
    return {"message": "Passkey registered successfully", "credential_id": credential.id}


# ============ 登录流程 ============

@router.post("/login/options", response_model=LoginOptionsResponse)
async def get_login_options(
    request: LoginOptionsRequest,
    session: Session = Depends(get_session)
):
    """
    获取 Passkey 登录选项

    返回 WebAuthn 认证参数，前端使用 navigator.credentials.get() 获取凭证
    """
    user = get_user_by_email(request.email, session)

    if not user:
        # 为了防止用户枚举，返回假的挑战
        options = generate_authentication_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            allow_credentials=[],
        )
        return LoginOptionsResponse(options=json.loads(options_to_json(options)))

    # 获取用户的 Passkey
    statement = select(WebAuthnCredential).where(
        WebAuthnCredential.user_id == user.id
    )
    credentials = session.exec(statement).all()

    if not credentials:
        raise HTTPException(status_code=400, detail="No passkeys registered for this account")

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in credentials
    ]

    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    # 存储挑战
    challenge_b64 = bytes_to_base64url(options.challenge)
    _challenges[challenge_b64] = {
        "user_id": user.id,
        "email": request.email,
        "type": "authentication",
    }

    return LoginOptionsResponse(options=json.loads(options_to_json(options)))


@router.post("/login/verify")
async def verify_login(
    request: LoginVerifyRequest,
    session: Session = Depends(get_session)
):
    """
    验证 Passkey 登录响应

    验证成功后返回访问令牌
    """
    user = get_user_by_email(request.email, session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 查找挑战
    challenge_b64 = None
    challenge_data = None

    for ch, data in list(_challenges.items()):
        if data.get("email") == request.email and data.get("type") == "authentication":
            challenge_b64 = ch
            challenge_data = data
            break

    if not challenge_data:
        raise HTTPException(status_code=400, detail="No pending authentication challenge")

    # 获取凭证
    credential_id_b64 = request.credential.get("id")
    statement = select(WebAuthnCredential).where(
        WebAuthnCredential.user_id == user.id,
        WebAuthnCredential.credential_id == credential_id_b64
    )
    stored_credential = session.exec(statement).first()

    if not stored_credential:
        del _challenges[challenge_b64]
        raise HTTPException(status_code=401, detail="Credential not found")

    try:
        verification = verify_authentication_response(
            credential=request.credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=base64url_to_bytes(stored_credential.public_key),
            credential_current_sign_count=stored_credential.sign_count,
        )
    except Exception as e:
        logger.error("WebAuthn authentication verification failed", error=str(e))
        del _challenges[challenge_b64]
        raise HTTPException(status_code=401, detail=f"Verification failed: {str(e)}")

    # 更新 sign_count
    stored_credential.sign_count = verification.new_sign_count
    stored_credential.last_used_at = datetime.now()
    session.add(stored_credential)
    session.commit()

    # 清理挑战
    del _challenges[challenge_b64]

    # 生成令牌
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id, session)

    logger.info("Passkey login successful", user_id=user.id)

    from config.settings import settings as app_settings
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": app_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_token,
    }


# ============ 凭证管理 ============

@router.get("/credentials", response_model=List[CredentialResponse])
async def list_credentials(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    列出用户的所有 Passkey
    """
    statement = select(WebAuthnCredential).where(
        WebAuthnCredential.user_id == current_user.id
    )
    credentials = session.exec(statement).all()

    return [
        CredentialResponse(
            id=cred.id,
            credential_id=cred.credential_id[:20] + "...",  # 截断显示
            device_name=cred.device_name,
            created_at=cred.created_at.isoformat(),
            last_used_at=cred.last_used_at.isoformat() if cred.last_used_at else None,
        )
        for cred in credentials
    ]


@router.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    删除指定的 Passkey
    """
    credential = session.get(WebAuthnCredential, credential_id)

    if not credential or credential.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Credential not found")

    # 检查是否是最后一个登录方式
    if not current_user.hashed_password:
        statement = select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == current_user.id
        )
        all_credentials = session.exec(statement).all()

        from sqlmodel import select as sql_select
        from db.models import OAuthAccount
        oauth_statement = sql_select(OAuthAccount).where(
            OAuthAccount.user_id == current_user.id
        )
        oauth_accounts = session.exec(oauth_statement).all()

        if len(all_credentials) <= 1 and not oauth_accounts:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete: this is your only login method"
            )

    session.delete(credential)
    session.commit()

    logger.info("Passkey deleted", user_id=current_user.id, credential_id=credential_id)
    return {"message": "Passkey deleted successfully"}
