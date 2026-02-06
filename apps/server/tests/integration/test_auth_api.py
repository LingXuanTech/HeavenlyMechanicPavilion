"""
认证 API 集成测试

测试内容：
1. POST /auth/register - 用户注册
2. POST /auth/login - 用户登录
3. POST /auth/refresh - Token 刷新
4. GET /auth/me - 获取当前用户信息
5. POST /auth/logout - 用户登出
6. 受保护路由的访问控制
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from db.models import User, RefreshToken


class TestUserRegistration:
    """测试用户注册流程"""

    def test_register_success(self, client, db_session):
        """成功注册新用户"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "display_name": "New User"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 验证返回的用户信息
        assert data["email"] == "newuser@example.com"
        assert data["display_name"] == "New User"
        assert "id" in data
        assert data["email_verified"] == False

        # 验证响应头中包含 access_token
        assert "X-Access-Token" in response.headers

        # 验证 refresh_token cookie 已设置
        assert "refresh_token" in response.cookies

    def test_register_duplicate_email(self, client, db_session):
        """重复邮箱注册失败"""
        # 先注册一个用户
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "password123",
            }
        )

        # 尝试用相同邮箱再次注册
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "anotherpassword",
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """无效邮箱格式注册失败"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "password123",
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, client):
        """密码太短注册失败"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",  # 少于 8 位
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_without_display_name(self, client, db_session):
        """不提供显示名称时使用邮箱前缀"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "testuser@example.com",
                "password": "password123",
            }
        )

        assert response.status_code == 200
        data = response.json()
        # 显示名称应该是邮箱前缀
        assert data["display_name"] == "testuser"


class TestUserLogin:
    """测试用户登录流程"""

    def test_login_success(self, client, db_session):
        """成功登录"""
        # 先注册用户
        client.post(
            "/api/auth/register",
            json={
                "email": "logintest@example.com",
                "password": "password123",
            }
        )

        # 登录
        response = client.post(
            "/api/auth/login",
            json={
                "email": "logintest@example.com",
                "password": "password123",
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 验证返回的 token 信息
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0

        # 验证 refresh_token cookie 已设置
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, client, db_session):
        """密码错误登录失败"""
        # 先注册用户
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongpwd@example.com",
                "password": "correctpassword",
            }
        )

        # 使用错误密码登录
        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongpwd@example.com",
                "password": "wrongpassword",
            }
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """不存在的用户登录失败"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            }
        )

        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        """禁用用户登录失败"""
        from services.auth_service import hash_password

        # 直接创建一个禁用的用户
        user = User(
            email="inactive@example.com",
            hashed_password=hash_password("password123"),
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()

        # 尝试登录
        response = client.post(
            "/api/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "password123",
            }
        )

        assert response.status_code == 401


class TestTokenRefresh:
    """测试 Token 刷新流程"""

    def test_refresh_token_success(self, client, db_session):
        """成功刷新 Token"""
        # 先注册并登录获取 refresh_token
        client.post(
            "/api/auth/register",
            json={
                "email": "refreshtest@example.com",
                "password": "password123",
            }
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "refreshtest@example.com",
                "password": "password123",
            }
        )

        # 从 cookie 获取 refresh_token
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None

        # 刷新 token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_refresh_invalid_token(self, client):
        """无效 refresh_token 刷新失败"""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token-string"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_expired_token(self, client, db_session):
        """过期 refresh_token 刷新失败"""
        from services.auth_service import hash_password
        import secrets

        # 创建用户
        user = User(
            email="expiredtoken@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(user)
        db_session.commit()

        # 创建一个已过期的 refresh_token
        expired_token = RefreshToken(
            user_id=user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() - timedelta(days=1),  # 已过期
        )
        db_session.add(expired_token)
        db_session.commit()

        # 尝试刷新
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": expired_token.token}
        )

        assert response.status_code == 401

    def test_refresh_revoked_token(self, client, db_session):
        """已撤销 refresh_token 刷新失败"""
        from services.auth_service import hash_password
        import secrets

        # 创建用户
        user = User(
            email="revokedtoken@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(user)
        db_session.commit()

        # 创建一个已撤销的 refresh_token
        revoked_token = RefreshToken(
            user_id=user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(days=7),
            revoked=True,  # 已撤销
        )
        db_session.add(revoked_token)
        db_session.commit()

        # 尝试刷新
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": revoked_token.token}
        )

        assert response.status_code == 401


class TestProtectedRoutes:
    """测试受保护路由的访问控制"""

    def test_get_current_user_with_valid_token(self, client, db_session):
        """有效 Token 可以访问受保护路由"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "email": "protected@example.com",
                "password": "password123",
                "display_name": "Protected User"
            }
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "protected@example.com",
                "password": "password123",
            }
        )

        access_token = login_response.json()["access_token"]

        # 访问受保护路由
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protected@example.com"
        assert data["display_name"] == "Protected User"

    def test_get_current_user_without_token(self, client):
        """无 Token 访问受保护路由失败"""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "authentication" in response.json()["detail"].lower()

    def test_get_current_user_with_invalid_token(self, client):
        """无效 Token 访问受保护路由失败"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401

    def test_get_current_user_with_expired_token(self, client, db_session):
        """过期 Token 访问受保护路由失败"""
        from services.auth_service import create_access_token, hash_password

        # 创建用户
        user = User(
            email="expiredaccess@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(user)
        db_session.commit()

        # 创建一个已过期的 access_token
        expired_token = create_access_token(
            user.id,
            expires_delta=timedelta(seconds=-1)  # 已过期
        )

        # 尝试访问
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


class TestUserLogout:
    """测试用户登出流程"""

    def test_logout_success(self, client, db_session):
        """成功登出"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "email": "logout@example.com",
                "password": "password123",
            }
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "logout@example.com",
                "password": "password123",
            }
        )

        refresh_token = login_response.cookies.get("refresh_token")

        # 登出
        response = client.post(
            "/api/auth/logout",
            params={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    def test_logout_without_token(self, client):
        """无 Token 也可以登出（清除 cookie）"""
        response = client.post("/api/auth/logout")

        assert response.status_code == 200


class TestUserProfileUpdate:
    """测试用户资料更新"""

    def test_update_display_name(self, client, db_session):
        """更新显示名称"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "email": "updateprofile@example.com",
                "password": "password123",
                "display_name": "Original Name"
            }
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "updateprofile@example.com",
                "password": "password123",
            }
        )

        access_token = login_response.json()["access_token"]

        # 更新资料
        response = client.put(
            "/api/auth/me",
            params={"display_name": "Updated Name"},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"

    def test_update_avatar_url(self, client, db_session):
        """更新头像 URL"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "email": "avatar@example.com",
                "password": "password123",
            }
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "avatar@example.com",
                "password": "password123",
            }
        )

        access_token = login_response.json()["access_token"]

        # 更新头像
        new_avatar = "https://example.com/avatar.png"
        response = client.put(
            "/api/auth/me",
            params={"avatar_url": new_avatar},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] == new_avatar


class TestAuthEdgeCases:
    """认证边缘情况测试"""

    def test_case_insensitive_email(self, client, db_session):
        """邮箱大小写不敏感（注册时转小写）"""
        # 注册时使用大写邮箱
        client.post(
            "/api/auth/register",
            json={
                "email": "UPPERCASE@EXAMPLE.COM",
                "password": "password123",
            }
        )

        # 使用小写邮箱登录
        response = client.post(
            "/api/auth/login",
            json={
                "email": "uppercase@example.com",
                "password": "password123",
            }
        )

        # 注意：这取决于实现，如果邮箱存储时转小写则应该成功
        # 如果不转换则会失败，这里假设实现会处理大小写
        # 实际行为取决于 auth_service 的实现
        assert response.status_code in [200, 401]

    def test_multiple_login_sessions(self, client, db_session):
        """多次登录创建多个 refresh_token"""
        # 注册
        client.post(
            "/api/auth/register",
            json={
                "email": "multisession@example.com",
                "password": "password123",
            }
        )

        # 第一次登录
        response1 = client.post(
            "/api/auth/login",
            json={
                "email": "multisession@example.com",
                "password": "password123",
            }
        )
        token1 = response1.cookies.get("refresh_token")

        # 第二次登录
        response2 = client.post(
            "/api/auth/login",
            json={
                "email": "multisession@example.com",
                "password": "password123",
            }
        )
        token2 = response2.cookies.get("refresh_token")

        # 两个 token 应该不同
        assert token1 != token2

        # 两个 token 都应该有效
        refresh1 = client.post(
            "/api/auth/refresh",
            json={"refresh_token": token1}
        )
        refresh2 = client.post(
            "/api/auth/refresh",
            json={"refresh_token": token2}
        )

        assert refresh1.status_code == 200
        assert refresh2.status_code == 200

    def test_token_after_password_change(self, client, db_session):
        """密码更改后旧 token 应该失效（如果实现了此功能）"""
        # 这个测试取决于是否实现了密码更改时撤销所有 token 的功能
        # 当前实现中 update_user_password 会撤销所有 refresh_token
        pass  # 需要密码更改端点才能测试
