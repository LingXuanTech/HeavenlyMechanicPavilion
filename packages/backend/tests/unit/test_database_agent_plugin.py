"""Unit tests for DatabaseAgentPlugin."""

import json
from unittest.mock import MagicMock

import pytest

from tradingagents.agents import DatabaseAgentPlugin, create_plugin_from_db_config
from tradingagents.agents.plugin_base import AgentCapability, AgentRole


class TestDatabaseAgentPlugin:
    """Test suite for DatabaseAgentPlugin."""

    def test_create_plugin_with_valid_config(self):
        """Test creating a plugin with valid configuration."""
        config = {
            "name": "custom_analyst",
            "role": "analyst",
            "capabilities": ["market_analysis"],
            "prompt_template": "You are a custom market analyst.",
            "description": "Custom market analyst",
            "version": "1.0.0",
            "requires_memory": False,
            "memory_name": None,
            "required_tools": ["get_stock_data"],
            "llm_type": "quick",
            "is_reserved": False,
            "slot_name": "custom_market",
        }

        plugin = DatabaseAgentPlugin(config=config)

        assert plugin.name == "custom_analyst"
        assert plugin.role == AgentRole.ANALYST
        assert plugin.capabilities == [AgentCapability.MARKET_ANALYSIS]
        assert plugin.prompt_template == "You are a custom market analyst."
        assert plugin.description == "Custom market analyst"
        assert plugin.version == "1.0.0"
        assert plugin.requires_memory is False
        assert plugin.memory_name is None
        assert plugin.required_tools == ["get_stock_data"]
        assert plugin.llm_type == "quick"
        assert plugin.is_reserved is False
        assert plugin.slot_name == "custom_market"

    def test_create_plugin_without_config_raises_error(self):
        """Test that creating plugin without config raises ValueError."""
        with pytest.raises(ValueError, match="requires configuration"):
            DatabaseAgentPlugin()

    def test_create_plugin_with_missing_required_fields(self):
        """Test that missing required fields raises ValueError."""
        config = {
            "name": "custom_analyst",
            "role": "analyst",
            # Missing capabilities and prompt_template
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            DatabaseAgentPlugin(config=config)

    def test_create_plugin_with_invalid_role(self):
        """Test that invalid role raises ValueError."""
        config = {
            "name": "custom_analyst",
            "role": "invalid_role",
            "capabilities": ["market_analysis"],
            "prompt_template": "Test prompt",
        }

        with pytest.raises(ValueError, match="Invalid role"):
            DatabaseAgentPlugin(config=config)

    def test_create_plugin_with_invalid_capability(self):
        """Test that invalid capability raises ValueError."""
        config = {
            "name": "custom_analyst",
            "role": "analyst",
            "capabilities": ["invalid_capability"],
            "prompt_template": "Test prompt",
        }

        with pytest.raises(ValueError, match="Invalid capability"):
            DatabaseAgentPlugin(config=config)

    def test_create_plugin_with_multiple_capabilities(self):
        """Test creating plugin with multiple capabilities."""
        config = {
            "name": "multi_analyst",
            "role": "analyst",
            "capabilities": ["market_analysis", "news_analysis", "social_sentiment"],
            "prompt_template": "You are a multi-capability analyst.",
        }

        plugin = DatabaseAgentPlugin(config=config)

        assert len(plugin.capabilities) == 3
        assert AgentCapability.MARKET_ANALYSIS in plugin.capabilities
        assert AgentCapability.NEWS_ANALYSIS in plugin.capabilities
        assert AgentCapability.SOCIAL_SENTIMENT in plugin.capabilities

    def test_create_plugin_with_defaults(self):
        """Test that optional fields use sensible defaults."""
        config = {
            "name": "simple_agent",
            "role": "analyst",
            "capabilities": ["market_analysis"],
            "prompt_template": "Simple prompt",
        }

        plugin = DatabaseAgentPlugin(config=config)

        # Check defaults
        assert plugin.description == "simple_agent agent"
        assert plugin.version == "1.0.0"
        assert plugin.requires_memory is False
        assert plugin.memory_name is None
        assert plugin.required_tools == []
        assert plugin.llm_type == "quick"
        assert plugin.is_reserved is False
        assert plugin.slot_name is None

    def test_create_node_returns_callable(self):
        """Test that create_node returns a callable function."""
        config = {
            "name": "test_agent",
            "role": "analyst",
            "capabilities": ["market_analysis"],
            "prompt_template": "Test prompt",
        }

        plugin = DatabaseAgentPlugin(config=config)
        llm = MagicMock()

        node = plugin.create_node(llm)

        assert callable(node)

    def test_supports_capability(self):
        """Test that supports_capability works correctly."""
        config = {
            "name": "test_agent",
            "role": "analyst",
            "capabilities": ["market_analysis", "news_analysis"],
            "prompt_template": "Test prompt",
        }

        plugin = DatabaseAgentPlugin(config=config)

        assert plugin.supports_capability(AgentCapability.MARKET_ANALYSIS)
        assert plugin.supports_capability(AgentCapability.NEWS_ANALYSIS)
        assert not plugin.supports_capability(AgentCapability.SOCIAL_SENTIMENT)

    def test_get_metadata(self):
        """Test that get_metadata returns correct metadata."""
        config = {
            "name": "test_agent",
            "role": "analyst",
            "capabilities": ["market_analysis"],
            "prompt_template": "Test prompt",
            "description": "Test description",
            "version": "2.0.0",
            "requires_memory": True,
            "memory_name": "test_memory",
            "required_tools": ["tool1", "tool2"],
            "llm_type": "deep",
            "is_reserved": False,
            "slot_name": "test_slot",
        }

        plugin = DatabaseAgentPlugin(config=config)
        metadata = plugin.get_metadata()

        assert metadata["name"] == "test_agent"
        assert metadata["role"] == "analyst"
        assert metadata["capabilities"] == ["market_analysis"]
        assert metadata["description"] == "Test description"
        assert metadata["version"] == "2.0.0"
        assert metadata["requires_memory"] is True
        assert metadata["memory_name"] == "test_memory"
        assert metadata["required_tools"] == ["tool1", "tool2"]
        assert metadata["llm_type"] == "deep"
        assert metadata["is_reserved"] is False
        assert metadata["slot_name"] == "test_slot"


class TestCreatePluginFromDbConfig:
    """Test suite for create_plugin_from_db_config helper function."""

    def test_create_plugin_from_valid_db_config(self):
        """Test creating plugin from valid database config."""
        db_config = MagicMock()
        db_config.name = "db_agent"
        db_config.role = "analyst"
        db_config.capabilities_json = json.dumps(["market_analysis"])
        db_config.prompt_template = "You are a database agent."
        db_config.description = "Database agent"
        db_config.version = "1.0.0"
        db_config.requires_memory = False
        db_config.memory_name = None
        db_config.required_tools_json = json.dumps(["tool1"])
        db_config.is_reserved = False
        db_config.slot_name = "db_slot"
        db_config.llm_config_json = json.dumps({"provider": "openai", "model": "gpt-4"})
        db_config.config_json = json.dumps({"param1": "value1"})
        db_config.metadata_json = json.dumps({"key": "value"})

        plugin = create_plugin_from_db_config(db_config)

        assert plugin is not None
        assert plugin.name == "db_agent"
        assert plugin.role == AgentRole.ANALYST
        assert plugin.capabilities == [AgentCapability.MARKET_ANALYSIS]
        assert plugin.prompt_template == "You are a database agent."

    def test_create_plugin_with_invalid_capabilities_json(self):
        """Test that invalid capabilities JSON returns None."""
        db_config = MagicMock()
        db_config.name = "bad_agent"
        db_config.role = "analyst"
        db_config.capabilities_json = "invalid json"
        db_config.prompt_template = "Test prompt"
        db_config.description = None
        db_config.version = "1.0.0"
        db_config.requires_memory = False
        db_config.memory_name = None
        db_config.required_tools_json = None
        db_config.is_reserved = False
        db_config.slot_name = None
        db_config.llm_config_json = None
        db_config.config_json = None
        db_config.metadata_json = None

        plugin = create_plugin_from_db_config(db_config)

        # Should return None due to malformed capabilities
        assert plugin is None

    def test_create_plugin_with_invalid_llm_config_json(self):
        """Test that invalid llm_config JSON is handled gracefully."""
        db_config = MagicMock()
        db_config.name = "agent_bad_llm"
        db_config.role = "analyst"
        db_config.capabilities_json = json.dumps(["market_analysis"])
        db_config.prompt_template = "Test prompt"
        db_config.description = None
        db_config.version = "1.0.0"
        db_config.requires_memory = False
        db_config.memory_name = None
        db_config.required_tools_json = None
        db_config.is_reserved = False
        db_config.slot_name = None
        db_config.llm_config_json = "invalid json"
        db_config.config_json = None
        db_config.metadata_json = None

        plugin = create_plugin_from_db_config(db_config)

        # Should still create plugin with empty llm_config
        assert plugin is not None
        assert plugin.config.get("llm_config") == {}

    def test_create_plugin_with_invalid_required_tools_json(self):
        """Test that invalid required_tools JSON is handled gracefully."""
        db_config = MagicMock()
        db_config.name = "agent_bad_tools"
        db_config.role = "analyst"
        db_config.capabilities_json = json.dumps(["market_analysis"])
        db_config.prompt_template = "Test prompt"
        db_config.description = None
        db_config.version = "1.0.0"
        db_config.requires_memory = False
        db_config.memory_name = None
        db_config.required_tools_json = "invalid json"
        db_config.is_reserved = False
        db_config.slot_name = None
        db_config.llm_config_json = None
        db_config.config_json = None
        db_config.metadata_json = None

        plugin = create_plugin_from_db_config(db_config)

        # Should still create plugin with empty required_tools
        assert plugin is not None
        assert plugin.required_tools == []

    def test_create_plugin_with_null_json_fields(self):
        """Test that None JSON fields are handled correctly."""
        db_config = MagicMock()
        db_config.name = "minimal_agent"
        db_config.role = "analyst"
        db_config.capabilities_json = json.dumps(["market_analysis"])
        db_config.prompt_template = "Minimal prompt"
        db_config.description = None
        db_config.version = "1.0.0"
        db_config.requires_memory = False
        db_config.memory_name = None
        db_config.required_tools_json = None
        db_config.is_reserved = False
        db_config.slot_name = None
        db_config.llm_config_json = None
        db_config.config_json = None
        db_config.metadata_json = None

        plugin = create_plugin_from_db_config(db_config)

        assert plugin is not None
        assert plugin.name == "minimal_agent"
        assert plugin.config.get("llm_config") == {}
        assert plugin.config.get("agent_config") == {}
        assert plugin.config.get("metadata") == {}

    def test_create_plugin_with_exception_returns_none(self):
        """Test that unexpected exceptions return None."""
        db_config = MagicMock()
        # Force an exception by making name raise an error
        db_config.name = property(lambda self: 1 / 0)

        plugin = create_plugin_from_db_config(db_config)

        assert plugin is None

    def test_create_plugin_with_various_roles(self):
        """Test creating plugins with different roles."""
        roles = [
            "analyst",
            "researcher",
            "manager",
            "trader",
            "risk_analyst",
            "risk_manager",
        ]

        for role in roles:
            db_config = MagicMock()
            db_config.name = f"{role}_agent"
            db_config.role = role
            db_config.capabilities_json = json.dumps(["market_analysis"])
            db_config.prompt_template = f"You are a {role}."
            db_config.description = None
            db_config.version = "1.0.0"
            db_config.requires_memory = False
            db_config.memory_name = None
            db_config.required_tools_json = None
            db_config.is_reserved = False
            db_config.slot_name = None
            db_config.llm_config_json = None
            db_config.config_json = None
            db_config.metadata_json = None

            plugin = create_plugin_from_db_config(db_config)

            assert plugin is not None
            assert plugin.role.value == role
