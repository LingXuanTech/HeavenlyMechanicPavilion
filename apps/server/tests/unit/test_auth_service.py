"""
AuthService 单元测试

覆盖:
1. 密码工具（哈希、验证）
2. JWT 令牌（创建、验证）
3. Refresh Token（创建、验证、撤销）
4. 用户操作（创建、查询、认证）
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_user_by_email,
    get_user_by_id,
    create_user,
    authenticate_user,
    update_user_password,
)
from db.models import User, RefreshToken


# =============================================================================
# 密码工具测试
# =============================================================================

class TestPasswordUtils:
    """密码哈希和验证测试"""

    def test_hash_password_returns_hash(self):
        """哈希密码返回哈希值"""
        password = "MySecureP@ssw0rd!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        # bcrypt 哈希以 $2b$ 开头
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_hash_password_different_for_same_input(self):
        """相同密码每次哈希结果不同（因为 salt）"""
        password = "TestPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """正确密码验证成功"""
        password = "CorrectPassword"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """错误密码验证失败"""
        password = "CorrectPassword"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty(self):
        """空密码验证失败"""
        hashed = hash_password("SomePassword")

        assert verify_password("", hashed) is False

    def test_hash_password_special_characters(self):
        """特殊字符密码哈希"""
        password = "P@$$w0rd!#%^&*()中文"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True


# =============================================================================
# JWT Access Token 测试
# =============================================================================

class TestAccessToken:
    """Access Token 创建和验证测试"""

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock 配置"""
        with patch("services.auth_service.settings") as mock:
            mock.JWT_SECRET_KEY = "test-secret-key-for-testing-only"
            mock.JWT_ALGORITHM = "HS256"
            mock.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock.REFRESH_TOKEN_EXPIRE_DAYS = 7
            yield mock

    def test_create_access_token(self):
        """创建 Access Token"""
        token = create_access_token(user_id=123)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        # JWT 格式：header.payload.signature
        assert token.count(".") == 2

    def test_verify_access_token_valid(self):
        """验证有效 Token"""
        token = create_access_token(user_id=456)
        user_id = verify_access_token(token)

        assert user_id == 456

    def test_verify_access_token_invalid(self):
        """验证无效 Token"""
        user_id = verify_access_token("invalid.token.here")

        assert user_id is None

    def test_verify_access_token_expired(self):
        """验证过期 Token"""
        # 创建一个已过期的 token
        token = create_access_token(
            user_id=789,
            expires_delta=timedelta(seconds=-1)  # 立即过期
        )
        user_id = verify_access_token(token)

        assert user_id is None

    def test_verify_access_token_wrong_type(self):
        """验证错误类型的 Token"""
        # 手动构造一个 refresh type 的 token
        from jose import jwt
        payload = {
            "sub": "100",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "type": "refresh"  # 错误类型
        }
        with patch("services.auth_service.settings") as mock:
            mock.JWT_SECRET_KEY = "test-secret-key"
            mock.JWT_ALGORITHM = "HS256"
            token = jwt.encode(payload, mock.JWT_SECRET_KEY, algorithm=mock.JWT_ALGORITHM)
            user_id = verify_access_token(token)

        assert user_id is None

    def test_create_access_token_custom_expiry(self):
        """自定义过期时间"""
        token = create_access_token(
            user_id=111,
            expires_delta=timedelta(hours=2)
        )
        user_id = verify_access_token(token)

        assert user_id == 111


# =============================================================================
# Refresh Token 测试
# =============================================================================

class TestRefreshToken:
    """Refresh Token 创建、验证和撤销测试"""

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock 配置"""
        with patch("services.auth_service.settings") as mock:
            mock.REFRESH_TOKEN_EXPIRE_DAYS = 7
            yield mock

    def test_create_refresh_token(self, db_session):
        """创建 Refresh Token"""
        token = create_refresh_token(user_id=1, session=db_session)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20  # urlsafe_b64 token

        # 验证数据库中存在
        from sqlmodel import select
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        db_token = db_session.exec(stmt).first()

        assert db_token is not None
        assert db_token.user_id == 1
        assert db_token.revoked is False

    def test_verify_refresh_token_valid(self, db_session):
        """验证有效 Refresh Token"""
        token = create_refresh_token(user_id=2, session=db_session)

        result = verify_refresh_token(token, db_session)

        assert result is not None
        assert result.user_id == 2
        assert result.token == token

    def test_verify_refresh_token_invalid(self, db_session):
        """验证无效 Refresh Token"""
        result = verify_refresh_token("nonexistent-token", db_session)

        assert result is None

    def test_verify_refresh_token_revoked(self, db_session):
        """验证已撤销的 Refresh Token"""
        token = create_refresh_token(user_id=3, session=db_session)

        # 撤销 token
        revoke_refresh_token(token, db_session)

        result = verify_refresh_token(token, db_session)
        assert result is None

    def test_verify_refresh_token_expired(self, db_session):
        """验证过期的 Refresh Token"""
        # 直接插入一个过期的 token
        expired_token = RefreshToken(
            user_id=4,
            token="expired-token-123",
            expires_at=datetime.utcnow() - timedelta(days=1),
            revoked=False,
        )
        db_session.add(expired_token)
        db_session.commit()

        result = verify_refresh_token("expired-token-123", db_session)
        assert result is None

    def test_revoke_refresh_token_success(self, db_session):
        """成功撤销 Refresh Token"""
        token = create_refresh_token(user_id=5, session=db_session)

        result = revoke_refresh_token(token, db_session)

        assert result is True

        # 验证已被撤销
        from sqlmodel import select
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        db_token = db_session.exec(stmt).first()
        assert db_token.revoked is True

    def test_revoke_refresh_token_not_found(self, db_session):
        """撤销不存在的 Token"""
        result = revoke_refresh_token("nonexistent-token", db_session)

        assert result is False

    def test_revoke_all_user_tokens(self, db_session):
        """撤销用户所有 Token"""
        # 创建多个 token
        token1 = create_refresh_token(user_id=6, session=db_session)
        token2 = create_refresh_token(user_id=6, session=db_session)
        token3 = create_refresh_token(user_id=6, session=db_session)

        count = revoke_all_user_tokens(user_id=6, session=db_session)

        assert count == 3

        # 验证所有 token 都被撤销
        assert verify_refresh_token(token1, db_session) is None
        assert verify_refresh_token(token2, db_session) is None
        assert verify_refresh_token(token3, db_session) is None

    def test_revoke_all_user_tokens_only_active(self, db_session):
        """只撤销活跃的 Token"""
        # 创建 token 并撤销一个
        token1 = create_refresh_token(user_id=7, session=db_session)
        token2 = create_refresh_token(user_id=7, session=db_session)
        revoke_refresh_token(token1, db_session)

        count = revoke_all_user_tokens(user_id=7, session=db_session)

        # 只有一个活跃的被撤销
        assert count == 1


# =============================================================================
# 用户操作测试
# =============================================================================

class TestUserOperations:
    """用户 CRUD 操作测试"""

    def test_create_user_with_password(self, db_session):
        """创建带密码的用户"""
        user = create_user(
            email="test@example.com",
            password="SecureP@ss123",
            display_name="Test User",
            session=db_session,
        )

        assert user is not None
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.hashed_password is not None
        assert user.hashed_password != "SecureP@ss123"  # 应该是哈希值

    def test_create_user_without_password(self, db_session):
        """创建 OAuth 用户（无密码）"""
        user = create_user(
            email="oauth@example.com",
            password=None,
            display_name="OAuth User",
            avatar_url="https://example.com/avatar.jpg",
            session=db_session,
        )

        assert user is not None
        assert user.hashed_password is None
        assert user.avatar_url == "https://example.com/avatar.jpg"

    def test_create_user_default_display_name(self, db_session):
        """默认显示名称为邮箱前缀"""
        user = create_user(
            email="john.doe@example.com",
            password="Password123",
            session=db_session,
        )

        assert user.display_name == "john.doe"

    def test_get_user_by_email_found(self, db_session):
        """通过邮箱查找用户 - 找到"""
        create_user(
            email="findme@example.com",
            password="Pass123",
            session=db_session,
        )

        user = get_user_by_email("findme@example.com", db_session)

        assert user is not None
        assert user.email == "findme@example.com"

    def test_get_user_by_email_not_found(self, db_session):
        """通过邮箱查找用户 - 未找到"""
        user = get_user_by_email("nonexistent@example.com", db_session)

        assert user is None

    def test_get_user_by_id_found(self, db_session):
        """通过 ID 查找用户 - 找到"""
        created = create_user(
            email="byid@example.com",
            password="Pass123",
            session=db_session,
        )

        user = get_user_by_id(created.id, db_session)

        assert user is not None
        assert user.id == created.id

    def test_get_user_by_id_not_found(self, db_session):
        """通过 ID 查找用户 - 未找到"""
        user = get_user_by_id(99999, db_session)

        assert user is None


# =============================================================================
# 用户认证测试
# =============================================================================

class TestUserAuthentication:
    """用户认证流程测试"""

    def test_authenticate_user_success(self, db_session):
        """认证成功"""
        create_user(
            email="auth@example.com",
            password="CorrectPassword",
            session=db_session,
        )

        user = authenticate_user("auth@example.com", "CorrectPassword", db_session)

        assert user is not None
        assert user.email == "auth@example.com"

    def test_authenticate_user_wrong_password(self, db_session):
        """密码错误"""
        create_user(
            email="wrongpw@example.com",
            password="CorrectPassword",
            session=db_session,
        )

        user = authenticate_user("wrongpw@example.com", "WrongPassword", db_session)

        assert user is None

    def test_authenticate_user_not_found(self, db_session):
        """用户不存在"""
        user = authenticate_user("nobody@example.com", "AnyPassword", db_session)

        assert user is None

    def test_authenticate_user_no_password(self, db_session):
        """OAuth 用户（无密码）认证失败"""
        create_user(
            email="oauth_only@example.com",
            password=None,
            session=db_session,
        )

        user = authenticate_user("oauth_only@example.com", "AnyPassword", db_session)

        assert user is None

    def test_authenticate_user_inactive(self, db_session):
        """非活跃用户认证失败"""
        created = create_user(
            email="inactive@example.com",
            password="Password123",
            session=db_session,
        )
        # 手动设置为非活跃
        created.is_active = False
        db_session.add(created)
        db_session.commit()

        user = authenticate_user("inactive@example.com", "Password123", db_session)

        assert user is None


# =============================================================================
# 密码更新测试
# =============================================================================

class TestPasswordUpdate:
    """密码更新测试"""

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock 配置"""
        with patch("services.auth_service.settings") as mock:
            mock.REFRESH_TOKEN_EXPIRE_DAYS = 7
            yield mock

    def test_update_user_password(self, db_session):
        """更新用户密码"""
        user = create_user(
            email="updatepw@example.com",
            password="OldPassword",
            session=db_session,
        )

        # 创建一些 refresh token
        token1 = create_refresh_token(user.id, db_session)
        token2 = create_refresh_token(user.id, db_session)

        # 更新密码
        update_user_password(user, "NewPassword", db_session)

        # 验证新密码有效
        assert verify_password("NewPassword", user.hashed_password) is True
        assert verify_password("OldPassword", user.hashed_password) is False

        # 验证所有 refresh token 被撤销
        assert verify_refresh_token(token1, db_session) is None
        assert verify_refresh_token(token2, db_session) is None

    def test_update_user_password_updates_timestamp(self, db_session):
        """更新密码时更新时间戳"""
        user = create_user(
            email="timestamp@example.com",
            password="Password",
            session=db_session,
        )
        original_updated_at = user.updated_at

        # 短暂延迟确保时间戳不同
        import time
        time.sleep(0.01)

        update_user_password(user, "NewPassword", db_session)

        assert user.updated_at > original_updated_at
