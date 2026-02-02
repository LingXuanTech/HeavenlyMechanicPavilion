"""
AIConfigService 单元测试

覆盖:
1. 加密/解密（API Key）
2. 密钥脱敏
3. LLM 实例创建
4. 配置刷新
5. 降级机制
6. CRUD 操作
"""
import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from cryptography.fernet import Fernet

from services.ai_config_service import AIConfigService
from db.models import AIProvider, AIProviderType, AIModelConfig


# =============================================================================
# 加密解密测试
# =============================================================================

class TestEncryption:
    """API Key 加密解密测试"""

    @pytest.fixture
    def service(self):
        """创建一个新的 AIConfigService 实例（隔离测试）"""
        # 重置单例
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        AIConfigService._providers_cache = {}
        AIConfigService._model_configs_cache = {}
        AIConfigService._llm_instances = {}
        AIConfigService._last_refresh = None

        with patch.object(AIConfigService, '_ensure_default_configs'):
            service = AIConfigService()
        return service

    def test_encrypt_and_decrypt_key(self, service):
        """加密后可以正确解密"""
        original_key = "sk-test-api-key-12345"

        encrypted = service._encrypt_key(original_key)
        decrypted = service._decrypt_key(encrypted)

        assert encrypted != original_key  # 加密后应该不同
        assert decrypted == original_key  # 解密后应该恢复

    def test_encrypt_empty_key(self, service):
        """加密空字符串返回空字符串"""
        assert service._encrypt_key("") == ""
        assert service._encrypt_key(None) == ""

    def test_decrypt_empty_key(self, service):
        """解密空字符串返回空字符串"""
        assert service._decrypt_key("") == ""
        assert service._decrypt_key(None) == ""

    def test_decrypt_unencrypted_key(self, service):
        """解密未加密的字符串返回原值（降级处理）"""
        plain_key = "not-encrypted-key"
        # 这应该触发解密失败，返回原值
        result = service._decrypt_key(plain_key)
        assert result == plain_key


# =============================================================================
# 密钥脱敏测试
# =============================================================================

class TestMaskKey:
    """API Key 脱敏测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        with patch.object(AIConfigService, '_ensure_default_configs'):
            return AIConfigService()

    def test_mask_normal_key(self, service):
        """正常长度密钥脱敏"""
        key = "sk-1234567890abcdef"
        masked = service._mask_key(key)

        assert masked.startswith("sk-1")  # 前4字符
        assert masked.endswith("cdef")   # 后4字符
        assert "****" in masked           # 中间脱敏
        assert len(masked) == len(key)    # 长度一致

    def test_mask_short_key(self, service):
        """短密钥直接返回 ****"""
        assert service._mask_key("short") == "****"
        assert service._mask_key("1234567") == "****"

    def test_mask_empty_key(self, service):
        """空密钥返回 ****"""
        assert service._mask_key("") == "****"
        assert service._mask_key(None) == "****"


# =============================================================================
# LLM 实例创建测试
# =============================================================================

class TestCreateLLMInstance:
    """LLM 实例创建测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        AIConfigService._providers_cache = {}
        AIConfigService._model_configs_cache = {}
        AIConfigService._llm_instances = {}
        with patch.object(AIConfigService, '_ensure_default_configs'):
            return AIConfigService()

    def test_create_openai_instance(self, service):
        """创建 OpenAI LLM 实例"""
        provider = AIProvider(
            id=1,
            name="OpenAI",
            provider_type=AIProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            api_key=service._encrypt_key("sk-test-key"),
            models=json.dumps(["gpt-4o"]),
            is_enabled=True,
        )

        with patch("services.ai_config_service.ChatOpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            MockOpenAI.return_value = mock_instance

            llm = service._create_llm_instance(provider, "gpt-4o")

            MockOpenAI.assert_called_once_with(
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-test-key",
            )
            assert llm == mock_instance

    def test_create_openai_compatible_instance(self, service):
        """创建 OpenAI 兼容 LLM 实例"""
        provider = AIProvider(
            id=2,
            name="OpenRouter",
            provider_type=AIProviderType.OPENAI_COMPATIBLE,
            base_url="https://openrouter.ai/api/v1",
            api_key=service._encrypt_key("or-test-key"),
            models=json.dumps(["anthropic/claude-3"]),
            is_enabled=True,
        )

        with patch("services.ai_config_service.ChatOpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            MockOpenAI.return_value = mock_instance

            llm = service._create_llm_instance(provider, "anthropic/claude-3")

            MockOpenAI.assert_called_once_with(
                model="anthropic/claude-3",
                base_url="https://openrouter.ai/api/v1",
                api_key="or-test-key",
            )

    def test_create_google_instance(self, service):
        """创建 Google Gemini LLM 实例"""
        provider = AIProvider(
            id=3,
            name="Google",
            provider_type=AIProviderType.GOOGLE,
            api_key=service._encrypt_key("AIza-test-key"),
            models=json.dumps(["gemini-1.5-flash"]),
            is_enabled=True,
        )

        with patch("services.ai_config_service.ChatGoogleGenerativeAI") as MockGoogle:
            mock_instance = MagicMock()
            MockGoogle.return_value = mock_instance

            llm = service._create_llm_instance(provider, "gemini-1.5-flash")

            MockGoogle.assert_called_once_with(
                model="gemini-1.5-flash",
                google_api_key="AIza-test-key",
            )

    def test_create_anthropic_instance(self, service):
        """创建 Anthropic Claude LLM 实例"""
        provider = AIProvider(
            id=4,
            name="Anthropic",
            provider_type=AIProviderType.ANTHROPIC,
            api_key=service._encrypt_key("sk-ant-test-key"),
            models=json.dumps(["claude-3-sonnet"]),
            is_enabled=True,
        )

        with patch("services.ai_config_service.ChatAnthropic") as MockAnthropic:
            mock_instance = MagicMock()
            MockAnthropic.return_value = mock_instance

            llm = service._create_llm_instance(provider, "claude-3-sonnet")

            MockAnthropic.assert_called_once_with(
                model="claude-3-sonnet",
                api_key="sk-ant-test-key",
            )

    def test_create_deepseek_instance(self, service):
        """创建 DeepSeek LLM 实例"""
        provider = AIProvider(
            id=5,
            name="DeepSeek",
            provider_type=AIProviderType.DEEPSEEK,
            base_url="https://api.deepseek.com/v1",
            api_key=service._encrypt_key("ds-test-key"),
            models=json.dumps(["deepseek-chat"]),
            is_enabled=True,
        )

        with patch("services.ai_config_service.ChatOpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            MockOpenAI.return_value = mock_instance

            llm = service._create_llm_instance(provider, "deepseek-chat")

            MockOpenAI.assert_called_once_with(
                model="deepseek-chat",
                base_url="https://api.deepseek.com/v1",
                api_key="ds-test-key",
            )


# =============================================================================
# 获取 LLM 测试
# =============================================================================

class TestGetLLM:
    """get_llm() 方法测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        AIConfigService._providers_cache = {}
        AIConfigService._model_configs_cache = {}
        AIConfigService._llm_instances = {}
        with patch.object(AIConfigService, '_ensure_default_configs'):
            return AIConfigService()

    def test_get_llm_from_cache(self, service):
        """从缓存获取 LLM"""
        mock_llm = MagicMock()
        service._llm_instances["deep_think"] = mock_llm
        # 设置 model_configs_cache 以防止 refresh_config 被调用
        service._model_configs_cache = {"deep_think": MagicMock(provider_id=1, model_name="gpt-4o")}

        result = service.get_llm("deep_think")

        assert result == mock_llm

    def test_get_llm_creates_instance(self, service):
        """创建并缓存 LLM 实例"""
        provider = AIProvider(
            id=1,
            name="OpenAI",
            provider_type=AIProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            api_key=service._encrypt_key("sk-test"),
            models=json.dumps(["gpt-4o"]),
            is_enabled=True,
        )
        config = AIModelConfig(
            config_key="deep_think",
            provider_id=1,
            model_name="gpt-4o",
        )

        service._providers_cache = {1: provider}
        service._model_configs_cache = {"deep_think": config}

        with patch("services.ai_config_service.ChatOpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            MockOpenAI.return_value = mock_instance

            result = service.get_llm("deep_think")

            assert result == mock_instance
            assert service._llm_instances["deep_think"] == mock_instance

    def test_get_llm_fallback_google(self, service):
        """降级到 Google API"""
        service._model_configs_cache = {}  # 无配置

        with patch("services.ai_config_service.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = "AIza-test"
            mock_settings.OPENAI_API_KEY = None

            with patch("services.ai_config_service.ChatGoogleGenerativeAI") as MockGoogle:
                mock_instance = MagicMock()
                MockGoogle.return_value = mock_instance

                result = service.get_llm("quick_think")

                MockGoogle.assert_called_once_with(
                    model="gemini-1.5-flash",
                    google_api_key="AIza-test",
                )

    def test_get_llm_fallback_openai(self, service):
        """降级到 OpenAI API"""
        service._model_configs_cache = {}  # 无配置

        with patch("services.ai_config_service.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = None
            mock_settings.OPENAI_API_KEY = "sk-test"

            with patch("services.ai_config_service.ChatOpenAI") as MockOpenAI:
                mock_instance = MagicMock()
                MockOpenAI.return_value = mock_instance

                result = service.get_llm("deep_think")

                MockOpenAI.assert_called_once_with(
                    model="gpt-4o",
                    api_key="sk-test",
                )

    def test_get_llm_no_provider_raises(self, service):
        """无可用提供商抛出异常"""
        service._model_configs_cache = {}

        with patch("services.ai_config_service.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = None
            mock_settings.OPENAI_API_KEY = None

            with pytest.raises(ValueError) as exc_info:
                service.get_llm("deep_think")

            assert "No AI provider configured" in str(exc_info.value)


# =============================================================================
# 配置刷新测试
# =============================================================================

class TestRefreshConfig:
    """配置刷新测试"""

    def test_refresh_config_clears_llm_cache(self, db_session):
        """刷新配置清除 LLM 实例缓存"""
        # 重置单例
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        AIConfigService._providers_cache = {}
        AIConfigService._model_configs_cache = {}
        AIConfigService._llm_instances = {"old_key": MagicMock()}

        with patch.object(AIConfigService, '_ensure_default_configs'):
            service = AIConfigService()

        # 预设缓存
        service._llm_instances["test_key"] = MagicMock()

        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.exec.return_value.all.return_value = []
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                service.refresh_config()

        assert service._llm_instances == {}


# =============================================================================
# 状态获取测试
# =============================================================================

class TestGetStatus:
    """服务状态测试"""

    def test_get_status(self):
        """获取服务状态"""
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        AIConfigService._providers_cache = {1: MagicMock(), 2: MagicMock()}
        AIConfigService._model_configs_cache = {"deep_think": MagicMock()}
        AIConfigService._llm_instances = {"deep_think": MagicMock()}
        AIConfigService._last_refresh = datetime.now()

        with patch.object(AIConfigService, '_ensure_default_configs'):
            service = AIConfigService()

        status = service.get_status()

        assert status["initialized"] is True
        assert status["providers_count"] == 2
        assert status["configs_count"] == 1
        assert "deep_think" in status["cached_llms"]
        assert status["last_refresh"] is not None


# =============================================================================
# CRUD 操作测试
# =============================================================================

class TestCRUDOperations:
    """CRUD 操作测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        AIConfigService._providers_cache = {}
        AIConfigService._model_configs_cache = {}
        AIConfigService._llm_instances = {}
        with patch.object(AIConfigService, '_ensure_default_configs'):
            return AIConfigService()

    @pytest.mark.asyncio
    async def test_list_providers(self, service, db_session):
        """列出所有提供商"""
        # 添加测试数据
        provider = AIProvider(
            name="Test Provider",
            provider_type=AIProviderType.OPENAI,
            base_url="https://api.test.com",
            api_key=service._encrypt_key("sk-test-12345678901234567890"),
            models=json.dumps(["model-1", "model-2"]),
            is_enabled=True,
            priority=1,
        )
        db_session.add(provider)
        db_session.commit()

        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.exec.return_value.all.return_value = [provider]
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                providers = await service.list_providers()

        assert len(providers) == 1
        assert providers[0]["name"] == "Test Provider"
        assert "api_key_masked" in providers[0]
        assert providers[0]["api_key_masked"].startswith("sk-t")
        assert "****" in providers[0]["api_key_masked"]

    @pytest.mark.asyncio
    async def test_create_provider(self, service, db_session):
        """创建新提供商"""
        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_provider = AIProvider(
                    id=1,
                    name="New Provider",
                    provider_type=AIProviderType.OPENAI_COMPATIBLE,
                )
                mock_session.add = MagicMock()
                mock_session.commit = MagicMock()
                mock_session.refresh = MagicMock(side_effect=lambda p: setattr(p, 'id', 1))
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                with patch.object(service, 'refresh_config'):
                    result = await service.create_provider({
                        "name": "New Provider",
                        "provider_type": "openai_compatible",
                        "base_url": "https://api.new.com",
                        "api_key": "new-api-key",
                        "models": ["model-a"],
                    })

        assert "id" in result
        assert result["name"] == "New Provider"

    @pytest.mark.asyncio
    async def test_delete_provider(self, service, db_session):
        """删除提供商"""
        provider = AIProvider(
            id=1,
            name="To Delete",
            provider_type=AIProviderType.OPENAI,
            api_key="key",
            models="[]",
        )

        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.get.return_value = provider
                mock_session.delete = MagicMock()
                mock_session.commit = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                with patch.object(service, 'refresh_config'):
                    result = await service.delete_provider(1)

        assert result is True
        mock_session.delete.assert_called_once_with(provider)

    @pytest.mark.asyncio
    async def test_delete_provider_not_found(self, service, db_session):
        """删除不存在的提供商"""
        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.get.return_value = None
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                result = await service.delete_provider(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_test_provider_success(self, service, db_session):
        """测试提供商连接成功"""
        provider = AIProvider(
            id=1,
            name="Test",
            provider_type=AIProviderType.OPENAI,
            api_key=service._encrypt_key("sk-test"),
            models=json.dumps(["gpt-4o-mini"]),
        )

        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.get.return_value = provider
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                mock_llm = AsyncMock()
                mock_llm.ainvoke.return_value = MagicMock(content="OK")

                with patch.object(service, '_create_llm_instance', return_value=mock_llm):
                    result = await service.test_provider(1)

        assert result["success"] is True
        assert result["model"] == "gpt-4o-mini"
        assert "OK" in result["response_preview"]

    @pytest.mark.asyncio
    async def test_test_provider_failure(self, service, db_session):
        """测试提供商连接失败"""
        provider = AIProvider(
            id=1,
            name="Test",
            provider_type=AIProviderType.OPENAI,
            api_key=service._encrypt_key("sk-invalid"),
            models=json.dumps(["gpt-4o"]),
        )

        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.get.return_value = provider
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                with patch.object(
                    service, '_create_llm_instance',
                    side_effect=Exception("Invalid API key")
                ):
                    result = await service.test_provider(1)

        assert result["success"] is False
        assert "Invalid API key" in result["error"]

    @pytest.mark.asyncio
    async def test_test_provider_not_found(self, service, db_session):
        """测试不存在的提供商"""
        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.get.return_value = None
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                result = await service.test_provider(999)

        assert result["success"] is False
        assert "not found" in result["error"]


# =============================================================================
# 模型配置测试
# =============================================================================

class TestModelConfigOperations:
    """模型配置操作测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        AIConfigService._instance = None
        AIConfigService._encryption_key = None
        AIConfigService._providers_cache = {}
        AIConfigService._model_configs_cache = {}
        AIConfigService._llm_instances = {}
        with patch.object(AIConfigService, '_ensure_default_configs'):
            return AIConfigService()

    @pytest.mark.asyncio
    async def test_get_model_configs(self, service, db_session):
        """获取所有模型配置"""
        provider = AIProvider(
            id=1,
            name="OpenAI",
            provider_type=AIProviderType.OPENAI,
            api_key="key",
            models="[]",
        )
        config = AIModelConfig(
            config_key="deep_think",
            provider_id=1,
            model_name="gpt-4o",
            is_active=True,
        )

        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.exec.return_value.all.return_value = [config]
                mock_session.get.return_value = provider
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                configs = await service.get_model_configs()

        assert len(configs) == 1
        assert configs[0]["config_key"] == "deep_think"
        assert configs[0]["provider_name"] == "OpenAI"
        assert configs[0]["model_name"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_update_model_config_existing(self, service, db_session):
        """更新现有模型配置"""
        existing_config = AIModelConfig(
            config_key="quick_think",
            provider_id=1,
            model_name="old-model",
        )

        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.exec.return_value.first.return_value = existing_config
                mock_session.commit = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                with patch.object(service, 'refresh_config'):
                    result = await service.update_model_config(
                        config_key="quick_think",
                        provider_id=2,
                        model_name="new-model",
                    )

        assert result["config_key"] == "quick_think"
        assert result["updated"] is True
        assert existing_config.provider_id == 2
        assert existing_config.model_name == "new-model"

    @pytest.mark.asyncio
    async def test_update_model_config_create_new(self, service, db_session):
        """创建新模型配置"""
        with patch("services.ai_config_service.engine", db_session.get_bind()):
            with patch("services.ai_config_service.Session") as MockSession:
                mock_session = MagicMock()
                mock_session.exec.return_value.first.return_value = None  # 不存在
                mock_session.add = MagicMock()
                mock_session.commit = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)

                with patch.object(service, 'refresh_config'):
                    result = await service.update_model_config(
                        config_key="synthesis",
                        provider_id=1,
                        model_name="gemini-1.5-flash",
                    )

        assert result["config_key"] == "synthesis"
        assert result["updated"] is True
        mock_session.add.assert_called_once()
