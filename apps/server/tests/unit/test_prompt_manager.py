"""
PromptManager 单元测试

覆盖:
1. 单例模式
2. YAML 加载
3. Prompt 获取（含变量注入）
4. 热加载（文件修改检测）
5. 错误处理
"""
import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, MagicMock

from services.prompt_manager import PromptManager, prompt_manager


# =============================================================================
# 辅助工具
# =============================================================================

def create_temp_prompts(content: dict) -> str:
    """创建临时 YAML 文件并返回路径"""
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        yaml.dump(content, f, allow_unicode=True)
    return path


# =============================================================================
# 单例测试
# =============================================================================

class TestPromptManagerSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert prompt_manager is not None
        assert isinstance(prompt_manager, PromptManager)

    def test_singleton_same_instance(self):
        """多次实例化返回同一对象"""
        instance1 = PromptManager()
        instance2 = PromptManager()
        assert instance1 is instance2


# =============================================================================
# Prompt 获取测试
# =============================================================================

class TestGetPrompt:
    """Prompt 获取测试"""

    def test_get_existing_prompt(self):
        """获取存在的 prompt"""
        pm = PromptManager()
        pm._prompts = {
            "analyst": {
                "system": "You are a financial analyst.",
                "user": "Analyze {symbol}.",
            }
        }

        result = pm.get_prompt("analyst", {"symbol": "AAPL"})

        assert result["system"] == "You are a financial analyst."
        assert result["user"] == "Analyze AAPL."

    def test_get_nonexistent_prompt(self):
        """获取不存在的 prompt"""
        pm = PromptManager()
        pm._prompts = {}

        result = pm.get_prompt("nonexistent")

        assert result["system"] == ""
        assert result["user"] == ""

    def test_get_prompt_no_context(self):
        """获取 prompt 无上下文"""
        pm = PromptManager()
        pm._prompts = {
            "simple": {
                "system": "You are an assistant.",
                "user": "Hello.",
            }
        }

        result = pm.get_prompt("simple")

        assert result["system"] == "You are an assistant."
        assert result["user"] == "Hello."

    def test_get_prompt_with_context(self):
        """获取 prompt 带上下文变量"""
        pm = PromptManager()
        pm._prompts = {
            "analyst": {
                "system": "Analyze {symbol} in {market}.",
                "user": "Data: {data}",
            }
        }

        result = pm.get_prompt("analyst", {
            "symbol": "AAPL",
            "market": "US",
            "data": "price=150",
        })

        assert "AAPL" in result["system"]
        assert "US" in result["system"]
        assert "price=150" in result["user"]

    def test_get_prompt_missing_context_variable(self):
        """缺少上下文变量时不崩溃"""
        pm = PromptManager()
        pm._prompts = {
            "analyst": {
                "system": "Analyze {symbol} in {market}.",
                "user": "Data: {data}",
            }
        }

        # 只提供部分变量
        result = pm.get_prompt("analyst", {"symbol": "AAPL"})

        # 缺少变量时返回原始模板
        assert "{market}" in result["system"]


# =============================================================================
# YAML 加载测试
# =============================================================================

class TestLoadPrompts:
    """YAML 加载测试"""

    def test_load_from_file(self):
        """从文件加载"""
        content = {
            "test_role": {
                "system": "System prompt",
                "user": "User prompt",
            }
        }
        path = create_temp_prompts(content)

        try:
            pm = object.__new__(PromptManager)
            pm._prompts = {}
            pm._last_mtime = 0

            with patch("services.prompt_manager.settings") as mock_settings:
                mock_settings.PROMPTS_YAML_PATH = path
                pm._load_prompts()

            assert "test_role" in pm._prompts
            assert pm._prompts["test_role"]["system"] == "System prompt"
        finally:
            os.unlink(path)

    def test_load_file_not_found(self):
        """文件不存在"""
        pm = object.__new__(PromptManager)
        pm._prompts = {}
        pm._last_mtime = 0

        with patch("services.prompt_manager.settings") as mock_settings:
            mock_settings.PROMPTS_YAML_PATH = "/nonexistent/path.yaml"
            pm._load_prompts()

        assert pm._prompts == {}

    def test_load_skips_unchanged_file(self):
        """文件未修改时跳过加载"""
        content = {"role": {"system": "v1", "user": "v1"}}
        path = create_temp_prompts(content)

        try:
            pm = object.__new__(PromptManager)
            pm._prompts = {"old_role": {"system": "old"}}
            pm._last_mtime = os.path.getmtime(path) + 1  # 设置为比文件更新

            with patch("services.prompt_manager.settings") as mock_settings:
                mock_settings.PROMPTS_YAML_PATH = path
                pm._load_prompts()

            # 不应该加载新内容
            assert "old_role" in pm._prompts
            assert "role" not in pm._prompts
        finally:
            os.unlink(path)

    def test_load_reloads_changed_file(self):
        """文件修改后重新加载"""
        content = {"role": {"system": "v1", "user": "v1"}}
        path = create_temp_prompts(content)

        try:
            pm = object.__new__(PromptManager)
            pm._prompts = {}
            pm._last_mtime = 0  # 旧时间戳

            with patch("services.prompt_manager.settings") as mock_settings:
                mock_settings.PROMPTS_YAML_PATH = path
                pm._load_prompts()

            assert "role" in pm._prompts
            assert pm._prompts["role"]["system"] == "v1"
        finally:
            os.unlink(path)

    def test_load_handles_yaml_error(self):
        """YAML 解析错误处理"""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, 'w') as f:
            f.write("invalid: yaml: content: [")

        try:
            pm = object.__new__(PromptManager)
            pm._prompts = {}
            pm._last_mtime = 0

            with patch("services.prompt_manager.settings") as mock_settings:
                mock_settings.PROMPTS_YAML_PATH = path
                # 不应抛出异常
                pm._load_prompts()
        finally:
            os.unlink(path)
