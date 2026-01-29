"""OAuth 2.0 提供商配置"""

from authlib.integrations.starlette_client import OAuth
from config.settings import settings

oauth = OAuth()

# Google OAuth
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# GitHub OAuth
if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
    oauth.register(
        name="github",
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )


def get_enabled_providers() -> list[str]:
    """获取已配置的 OAuth 提供商列表"""
    providers = []
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        providers.append("google")
    if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
        providers.append("github")
    return providers
