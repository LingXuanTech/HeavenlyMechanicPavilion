"""
AI 配置服务

统一管理 LLM 实例化，支持：
- 多提供商配置（OpenAI、Google、Anthropic、DeepSeek 等）
- OpenAI 兼容模式（NewAPI/OneAPI/OpenRouter）
- 配置热更新
- API Key 加密存储
"""
import json
import os
import structlog
from datetime import datetime
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from sqlmodel import Session, select

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel

from db.models import AIProvider, AIProviderType, AIModelConfig, engine
from config.settings import settings

logger = structlog.get_logger()


class AIConfigService:
    """
    AI 配置服务 - 统一管理 LLM 实例化

    功能：
    1. 从数据库加载提供商配置
    2. 根据 config_key 创建 LLM 实例
    3. 支持配置热更新
    4. API Key 加密/解密
    """

    _instance = None
    _providers_cache: Dict[int, AIProvider] = {}
    _model_configs_cache: Dict[str, AIModelConfig] = {}
    _llm_instances: Dict[str, BaseChatModel] = {}
    _last_refresh: Optional[datetime] = None
    _encryption_key: Optional[bytes] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._encryption_key is None:
            self._init_encryption()
            self._ensure_default_configs()

    def _init_encryption(self):
        """初始化加密密钥"""
        key = os.getenv("AI_CONFIG_ENCRYPTION_KEY")
        if key:
            self._encryption_key = key.encode()
        else:
            # 如果没有配置密钥，生成一个临时密钥（仅用于开发）
            self._encryption_key = Fernet.generate_key()
            logger.warning(
                "AI_CONFIG_ENCRYPTION_KEY not set, using temporary key. "
                "API keys will not persist across restarts!"
            )

    def _encrypt_key(self, api_key: str) -> str:
        """加密 API Key"""
        if not api_key:
            return ""
        try:
            f = Fernet(self._encryption_key)
            return f.encrypt(api_key.encode()).decode()
        except Exception as e:
            logger.error("Failed to encrypt API key", error=str(e))
            return api_key  # 降级为明文存储

    def _decrypt_key(self, encrypted_key: str) -> str:
        """解密 API Key"""
        if not encrypted_key:
            return ""
        try:
            f = Fernet(self._encryption_key)
            return f.decrypt(encrypted_key.encode()).decode()
        except Exception:
            # 可能是未加密的旧数据
            return encrypted_key

    def _mask_key(self, api_key: str) -> str:
        """脱敏 API Key 用于前端显示"""
        if not api_key or len(api_key) < 8:
            return "****"
        return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"

    def _ensure_default_configs(self):
        """确保默认配置存在"""
        with Session(engine) as session:
            # 检查是否已有提供商配置
            existing = session.exec(select(AIProvider)).first()
            if existing:
                return

            logger.info("Creating default AI provider configurations")

            # 创建默认提供商
            default_providers = [
                AIProvider(
                    name="OpenAI Official",
                    provider_type=AIProviderType.OPENAI,
                    base_url="https://api.openai.com/v1",
                    api_key=self._encrypt_key(settings.OPENAI_API_KEY or ""),
                    models=json.dumps(["gpt-4o", "gpt-4o-mini", "o4-mini", "o3-mini"]),
                    is_enabled=bool(settings.OPENAI_API_KEY),
                    priority=1,
                ),
                AIProvider(
                    name="Google Gemini",
                    provider_type=AIProviderType.GOOGLE,
                    base_url=None,
                    api_key=self._encrypt_key(settings.GOOGLE_API_KEY or ""),
                    models=json.dumps(["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]),
                    is_enabled=bool(settings.GOOGLE_API_KEY),
                    priority=2,
                ),
                AIProvider(
                    name="Anthropic Claude",
                    provider_type=AIProviderType.ANTHROPIC,
                    base_url=None,
                    api_key="",
                    models=json.dumps(["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]),
                    is_enabled=False,
                    priority=3,
                ),
                AIProvider(
                    name="DeepSeek",
                    provider_type=AIProviderType.DEEPSEEK,
                    base_url="https://api.deepseek.com/v1",
                    api_key="",
                    models=json.dumps(["deepseek-chat", "deepseek-reasoner"]),
                    is_enabled=False,
                    priority=4,
                ),
                AIProvider(
                    name="OpenRouter",
                    provider_type=AIProviderType.OPENAI_COMPATIBLE,
                    base_url="https://openrouter.ai/api/v1",
                    api_key="",
                    models=json.dumps(["openai/gpt-4o", "anthropic/claude-3.5-sonnet"]),
                    is_enabled=False,
                    priority=5,
                ),
            ]

            for provider in default_providers:
                session.add(provider)

            session.commit()

            # 重新查询获取 ID
            providers = session.exec(select(AIProvider)).all()
            provider_map = {p.name: p.id for p in providers}

            # 创建默认模型配置
            default_configs = [
                AIModelConfig(
                    config_key="deep_think",
                    provider_id=provider_map.get("OpenAI Official") or provider_map.get("Google Gemini"),
                    model_name="o4-mini" if settings.OPENAI_API_KEY else "gemini-1.5-pro",
                ),
                AIModelConfig(
                    config_key="quick_think",
                    provider_id=provider_map.get("OpenAI Official") or provider_map.get("Google Gemini"),
                    model_name="gpt-4o-mini" if settings.OPENAI_API_KEY else "gemini-1.5-flash",
                ),
                AIModelConfig(
                    config_key="synthesis",
                    provider_id=provider_map.get("Google Gemini") or provider_map.get("OpenAI Official"),
                    model_name="gemini-1.5-flash" if settings.GOOGLE_API_KEY else "gpt-4o-mini",
                ),
            ]

            for config in default_configs:
                session.add(config)

            session.commit()
            logger.info("Default AI configurations created")

    def refresh_config(self):
        """刷新配置缓存"""
        with Session(engine) as session:
            # 加载所有启用的提供商
            providers = session.exec(
                select(AIProvider).where(AIProvider.is_enabled == True)
            ).all()
            self._providers_cache = {p.id: p for p in providers}

            # 加载所有模型配置
            configs = session.exec(select(AIModelConfig)).all()
            self._model_configs_cache = {c.config_key: c for c in configs}

            # 清除 LLM 实例缓存，下次使用时重新创建
            self._llm_instances.clear()

            self._last_refresh = datetime.now()
            logger.info(
                "AI config refreshed",
                providers=len(self._providers_cache),
                configs=len(self._model_configs_cache)
            )

    def _create_llm_instance(self, provider: AIProvider, model_name: str) -> BaseChatModel:
        """根据 provider_type 创建 LLM 实例"""
        api_key = self._decrypt_key(provider.api_key)

        if provider.provider_type in [
            AIProviderType.OPENAI,
            AIProviderType.OPENAI_COMPATIBLE,
            AIProviderType.DEEPSEEK,
        ]:
            # 所有 OpenAI 兼容的 API 统一使用 ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                base_url=provider.base_url or "https://api.openai.com/v1",
                api_key=api_key,
            )

        elif provider.provider_type == AIProviderType.GOOGLE:
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
            )

        elif provider.provider_type == AIProviderType.ANTHROPIC:
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
            )

        else:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")

    def get_llm(self, config_key: str) -> BaseChatModel:
        """
        获取 LLM 实例

        Args:
            config_key: 配置键，如 "deep_think", "quick_think", "synthesis"

        Returns:
            LLM 实例

        Raises:
            ValueError: 配置不存在或提供商未启用
        """
        # 确保配置已加载
        if not self._model_configs_cache:
            self.refresh_config()

        # 检查缓存
        if config_key in self._llm_instances:
            return self._llm_instances[config_key]

        # 获取模型配置
        config = self._model_configs_cache.get(config_key)
        if not config or not config.provider_id:
            # 降级到环境变量配置
            return self._fallback_llm(config_key)

        # 获取提供商
        provider = self._providers_cache.get(config.provider_id)
        if not provider:
            logger.warning(f"Provider {config.provider_id} not found, using fallback")
            return self._fallback_llm(config_key)

        # 创建 LLM 实例
        try:
            llm = self._create_llm_instance(provider, config.model_name)
            self._llm_instances[config_key] = llm
            logger.info(
                "LLM instance created",
                config_key=config_key,
                provider=provider.name,
                model=config.model_name
            )
            return llm
        except Exception as e:
            logger.error(
                "Failed to create LLM instance",
                config_key=config_key,
                error=str(e)
            )
            return self._fallback_llm(config_key)

    def _fallback_llm(self, config_key: str) -> BaseChatModel:
        """降级到环境变量配置的 LLM"""
        if settings.GOOGLE_API_KEY:
            model = "gemini-1.5-flash" if config_key == "quick_think" else "gemini-1.5-pro"
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        elif settings.OPENAI_API_KEY:
            model = "gpt-4o-mini" if config_key == "quick_think" else "gpt-4o"
            return ChatOpenAI(
                model=model,
                api_key=settings.OPENAI_API_KEY,
            )
        else:
            raise ValueError(
                "No AI provider configured. Please set up providers in AI Config "
                "or set GOOGLE_API_KEY/OPENAI_API_KEY environment variables."
            )

    # =========================================================================
    # CRUD 操作
    # =========================================================================

    async def list_providers(self) -> List[Dict[str, Any]]:
        """列出所有提供商（脱敏 API Key）"""
        with Session(engine) as session:
            providers = session.exec(
                select(AIProvider).order_by(AIProvider.priority)
            ).all()

            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "provider_type": p.provider_type.value,
                    "base_url": p.base_url,
                    "api_key_masked": self._mask_key(self._decrypt_key(p.api_key)),
                    "models": json.loads(p.models),
                    "is_enabled": p.is_enabled,
                    "priority": p.priority,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                }
                for p in providers
            ]

    async def get_provider(self, provider_id: int) -> Optional[Dict[str, Any]]:
        """获取单个提供商详情"""
        with Session(engine) as session:
            provider = session.get(AIProvider, provider_id)
            if not provider:
                return None

            return {
                "id": provider.id,
                "name": provider.name,
                "provider_type": provider.provider_type.value,
                "base_url": provider.base_url,
                "api_key_masked": self._mask_key(self._decrypt_key(provider.api_key)),
                "models": json.loads(provider.models),
                "is_enabled": provider.is_enabled,
                "priority": provider.priority,
            }

    async def create_provider(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新提供商"""
        with Session(engine) as session:
            provider = AIProvider(
                name=data["name"],
                provider_type=AIProviderType(data["provider_type"]),
                base_url=data.get("base_url"),
                api_key=self._encrypt_key(data.get("api_key", "")),
                models=json.dumps(data.get("models", [])),
                is_enabled=data.get("is_enabled", True),
                priority=data.get("priority", 99),
            )
            session.add(provider)
            session.commit()
            session.refresh(provider)

            self.refresh_config()

            return {
                "id": provider.id,
                "name": provider.name,
                "provider_type": provider.provider_type.value,
            }

    async def update_provider(self, provider_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新提供商"""
        with Session(engine) as session:
            provider = session.get(AIProvider, provider_id)
            if not provider:
                return None

            if "name" in data:
                provider.name = data["name"]
            if "provider_type" in data:
                provider.provider_type = AIProviderType(data["provider_type"])
            if "base_url" in data:
                provider.base_url = data["base_url"]
            if "api_key" in data and not data["api_key"].startswith("****"):
                # 只有非脱敏值才更新
                provider.api_key = self._encrypt_key(data["api_key"])
            if "models" in data:
                provider.models = json.dumps(data["models"])
            if "is_enabled" in data:
                provider.is_enabled = data["is_enabled"]
            if "priority" in data:
                provider.priority = data["priority"]

            provider.updated_at = datetime.now()
            session.commit()

            self.refresh_config()

            return {"id": provider.id, "name": provider.name, "updated": True}

    async def delete_provider(self, provider_id: int) -> bool:
        """删除提供商"""
        with Session(engine) as session:
            provider = session.get(AIProvider, provider_id)
            if not provider:
                return False

            session.delete(provider)
            session.commit()

            self.refresh_config()
            return True

    async def test_provider(self, provider_id: int) -> Dict[str, Any]:
        """测试提供商连接"""
        with Session(engine) as session:
            provider = session.get(AIProvider, provider_id)
            if not provider:
                return {"success": False, "error": "Provider not found"}

            try:
                models = json.loads(provider.models)
                if not models:
                    return {"success": False, "error": "No models configured"}

                # 使用第一个模型测试
                llm = self._create_llm_instance(provider, models[0])
                response = await llm.ainvoke("Say 'OK' if you can read this.")

                return {
                    "success": True,
                    "model": models[0],
                    "response_preview": str(response.content)[:100],
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    # =========================================================================
    # 模型配置管理
    # =========================================================================

    async def get_model_configs(self) -> List[Dict[str, Any]]:
        """获取所有模型配置"""
        with Session(engine) as session:
            configs = session.exec(select(AIModelConfig)).all()

            result = []
            for c in configs:
                provider = session.get(AIProvider, c.provider_id) if c.provider_id else None
                result.append({
                    "config_key": c.config_key,
                    "provider_id": c.provider_id,
                    "provider_name": provider.name if provider else None,
                    "model_name": c.model_name,
                    "is_active": c.is_active,
                    "updated_at": c.updated_at.isoformat(),
                })

            return result

    async def update_model_config(
        self, config_key: str, provider_id: int, model_name: str
    ) -> Dict[str, Any]:
        """更新模型配置"""
        with Session(engine) as session:
            config = session.exec(
                select(AIModelConfig).where(AIModelConfig.config_key == config_key)
            ).first()

            if config:
                config.provider_id = provider_id
                config.model_name = model_name
                config.updated_at = datetime.now()
            else:
                config = AIModelConfig(
                    config_key=config_key,
                    provider_id=provider_id,
                    model_name=model_name,
                )
                session.add(config)

            session.commit()

            self.refresh_config()

            return {"config_key": config_key, "updated": True}

    def get_openai_client_config(self) -> Optional[Dict[str, str]]:
        """获取 OpenAI 兼容的客户端配置（base_url + api_key）

        供 embedding、TTS、Responses API 等需要原生 OpenAI 客户端的场景使用。
        优先返回 OpenAI/OpenAI-Compatible/DeepSeek 类型的 provider。

        Returns:
            {"base_url": "...", "api_key": "..."} 或 None
        """
        if not self._providers_cache:
            self.refresh_config()

        openai_compatible_types = {
            AIProviderType.OPENAI,
            AIProviderType.OPENAI_COMPATIBLE,
            AIProviderType.DEEPSEEK,
        }

        # 按 priority 排序，找到第一个可用的 OpenAI 兼容 provider
        for provider in sorted(self._providers_cache.values(), key=lambda p: p.priority):
            if provider.provider_type in openai_compatible_types and provider.is_enabled:
                api_key = self._decrypt_key(provider.api_key)
                if api_key:
                    return {
                        "base_url": provider.base_url or "https://api.openai.com/v1",
                        "api_key": api_key,
                    }

        # 降级：检查环境变量
        if settings.OPENAI_API_KEY:
            return {
                "base_url": "https://api.openai.com/v1",
                "api_key": settings.OPENAI_API_KEY,
            }

        logger.debug("No OpenAI-compatible provider available")
        return None

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "initialized": bool(self._model_configs_cache),
            "providers_count": len(self._providers_cache),
            "configs_count": len(self._model_configs_cache),
            "cached_llms": list(self._llm_instances.keys()),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
        }


# 全局单例
ai_config_service = AIConfigService()
