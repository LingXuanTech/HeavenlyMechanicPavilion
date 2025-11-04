"""Integration tests for agent hot-reload functionality."""

import json

import pytest

from app.db.models import AgentConfig
from app.db.session import DatabaseManager
from app.schemas.agent_config import AgentConfigCreate, AgentConfigUpdate
from app.services.agent_config import AgentConfigService
from tradingagents.agents import get_agent_registry
from tradingagents.agents.plugin_base import AgentRole
from tradingagents.agents.plugin_loader import register_built_in_plugins


@pytest.fixture
async def agent_service(test_db: DatabaseManager):
    """Create an agent config service with test database."""
    async for session in test_db.get_session():
        service = AgentConfigService(session)
        # Initialize registry with built-in agents
        registry = get_agent_registry()
        registry.clear()
        register_built_in_plugins(registry)
        yield service
        # Clean up registry after test
        registry.clear()
        break


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentHotReload:
    """Integration tests for hot-reload of custom agents."""

    async def test_create_custom_agent_triggers_reload(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that creating a custom agent triggers hot-reload."""
        # Get initial count
        registry = get_agent_registry()
        initial_count = len(registry.list_plugins())

        # Create a custom agent via service
        agent_data = AgentConfigCreate(
            name="custom_crypto_analyst",
            agent_type="analyst",
            role="analyst",
            prompt_template="You are a cryptocurrency analyst.",
            capabilities=["market_analysis"],
            required_tools=["get_stock_data"],
            is_reserved=False,
            is_active=True,
            slot_name="crypto",
            description="Cryptocurrency market analyst",
        )

        agent = await agent_service.create_agent(agent_data)
        assert agent is not None

        # Check that agent is in registry
        plugin = registry.get_plugin("custom_crypto_analyst")
        assert plugin is not None
        assert plugin.name == "custom_crypto_analyst"
        assert plugin.role == AgentRole.ANALYST
        assert plugin.slot_name == "crypto"
        assert not plugin.is_reserved

        # Verify plugin count increased
        new_count = len(registry.list_plugins())
        assert new_count == initial_count + 1

    async def test_update_custom_agent_triggers_reload(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that updating a custom agent triggers hot-reload."""
        # Create a custom agent
        agent_data = AgentConfigCreate(
            name="update_test_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Original prompt",
            capabilities=["market_analysis"],
            is_reserved=False,
            is_active=True,
        )

        agent = await agent_service.create_agent(agent_data)
        agent_id = agent.id

        # Verify original plugin
        registry = get_agent_registry()
        plugin = registry.get_plugin("update_test_agent")
        assert plugin is not None
        assert plugin.prompt_template == "Original prompt"

        # Update the agent
        update_data = AgentConfigUpdate(
            prompt_template="Updated prompt",
            description="Updated description",
        )

        updated_agent = await agent_service.update_agent(agent_id, update_data)
        assert updated_agent is not None

        # Verify plugin was updated
        plugin = registry.get_plugin("update_test_agent")
        assert plugin is not None
        assert plugin.prompt_template == "Updated prompt"
        assert plugin.description == "Updated description"

    async def test_delete_custom_agent_triggers_reload(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that deleting a custom agent triggers hot-reload."""
        # Create a custom agent
        agent_data = AgentConfigCreate(
            name="delete_test_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Test prompt",
            capabilities=["market_analysis"],
            is_reserved=False,
            is_active=True,
        )

        agent = await agent_service.create_agent(agent_data)
        agent_id = agent.id

        # Verify plugin exists
        registry = get_agent_registry()
        plugin = registry.get_plugin("delete_test_agent")
        assert plugin is not None

        # Delete the agent
        success = await agent_service.delete_agent(agent_id)
        assert success

        # Verify plugin is removed
        plugin = registry.get_plugin("delete_test_agent")
        assert plugin is None

    async def test_hot_reload_with_slot_assignment(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that hot-reload correctly assigns slots."""
        # Create a custom agent with slot
        agent_data = AgentConfigCreate(
            name="slotted_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Test prompt",
            capabilities=["market_analysis"],
            is_reserved=False,
            is_active=True,
            slot_name="custom_slot",
        )

        agent = await agent_service.create_agent(agent_data)
        assert agent is not None

        # Verify slot assignment
        registry = get_agent_registry()
        plugin = registry.get_plugin_by_slot("custom_slot")
        assert plugin is not None
        assert plugin.name == "slotted_agent"

    async def test_hot_reload_skips_inactive_agents(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that hot-reload skips inactive agents."""
        # Create an inactive custom agent
        agent_data = AgentConfigCreate(
            name="inactive_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Test prompt",
            capabilities=["market_analysis"],
            is_reserved=False,
            is_active=False,
        )

        agent = await agent_service.create_agent(agent_data)
        assert agent is not None

        # Verify plugin is NOT in registry
        registry = get_agent_registry()
        plugin = registry.get_plugin("inactive_agent")
        assert plugin is None

    async def test_hot_reload_skips_reserved_agents_from_db(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that hot-reload skips reserved agents from database."""
        # Create a reserved agent directly in database (bypassing service validation)
        agent = AgentConfig(
            name="fake_reserved_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Test prompt",
            capabilities_json=json.dumps(["market_analysis"]),
            is_reserved=True,  # Marked as reserved
            is_active=True,
        )
        
        agent_service.session.add(agent)
        await agent_service.session.commit()

        # Trigger hot-reload
        await agent_service._trigger_hot_reload()

        # Verify reserved agent from DB is NOT loaded as custom plugin
        registry = get_agent_registry()
        plugin = registry.get_plugin("fake_reserved_agent")
        # Should be None because reserved agents from DB are filtered out
        assert plugin is None

    async def test_hot_reload_with_malformed_json(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that hot-reload handles malformed JSON gracefully."""
        # Create agent with malformed JSON directly in database
        agent = AgentConfig(
            name="malformed_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Test prompt",
            capabilities_json="invalid json",  # Malformed JSON
            is_reserved=False,
            is_active=True,
        )
        
        agent_service.session.add(agent)
        await agent_service.session.commit()

        # Trigger hot-reload should not fail
        await agent_service._trigger_hot_reload()

        # Verify malformed agent is not loaded
        registry = get_agent_registry()
        plugin = registry.get_plugin("malformed_agent")
        assert plugin is None

    async def test_hot_reload_with_multiple_custom_agents(
        self,
        agent_service: AgentConfigService,
    ):
        """Test hot-reload with multiple custom agents."""
        # Create multiple custom agents
        agent_names = [
            "custom_agent_1",
            "custom_agent_2",
            "custom_agent_3",
        ]

        registry = get_agent_registry()
        initial_count = len(registry.list_plugins())

        for name in agent_names:
            agent_data = AgentConfigCreate(
                name=name,
                agent_type="analyst",
                role="analyst",
                prompt_template=f"Prompt for {name}",
                capabilities=["market_analysis"],
                is_reserved=False,
                is_active=True,
            )

            agent = await agent_service.create_agent(agent_data)
            assert agent is not None

        # Verify all agents are in registry
        new_count = len(registry.list_plugins())
        assert new_count == initial_count + len(agent_names)

        for name in agent_names:
            plugin = registry.get_plugin(name)
            assert plugin is not None
            assert plugin.name == name

    async def test_hot_reload_preserves_built_in_agents(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that hot-reload preserves built-in agents."""
        # Get initial built-in agents
        registry = get_agent_registry()
        built_in_names = [
            "market_analyst",
            "social_analyst",
            "news_analyst",
            "fundamentals_analyst",
        ]

        # Verify built-in agents exist
        for name in built_in_names:
            assert registry.get_plugin(name) is not None

        # Create a custom agent (triggers reload)
        agent_data = AgentConfigCreate(
            name="custom_test_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Test prompt",
            capabilities=["market_analysis"],
            is_reserved=False,
            is_active=True,
        )

        agent = await agent_service.create_agent(agent_data)
        assert agent is not None

        # Verify built-in agents still exist after reload
        for name in built_in_names:
            plugin = registry.get_plugin(name)
            assert plugin is not None, f"Built-in agent {name} missing after reload"

    async def test_hot_reload_with_different_roles(
        self,
        agent_service: AgentConfigService,
    ):
        """Test hot-reload with agents of different roles."""
        agent_configs = [
            {
                "name": "custom_analyst",
                "agent_type": "analyst",
                "role": "analyst",
                "capabilities": ["market_analysis"],
            },
            {
                "name": "custom_researcher",
                "agent_type": "researcher",
                "role": "researcher",
                "capabilities": ["bull_research"],
            },
            {
                "name": "custom_risk_analyst",
                "agent_type": "risk_analyst",
                "role": "risk_analyst",
                "capabilities": ["risky_analysis"],
            },
        ]

        registry = get_agent_registry()

        for config in agent_configs:
            agent_data = AgentConfigCreate(
                name=config["name"],
                agent_type=config["agent_type"],
                role=config["role"],
                prompt_template=f"Prompt for {config['name']}",
                capabilities=config["capabilities"],
                is_reserved=False,
                is_active=True,
            )

            agent = await agent_service.create_agent(agent_data)
            assert agent is not None

            # Verify plugin is registered with correct role
            plugin = registry.get_plugin(config["name"])
            assert plugin is not None
            assert plugin.role.value == config["role"]

    async def test_hot_reload_override_behavior(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that hot-reload allows override of existing custom plugins."""
        # Create a custom agent
        agent_data = AgentConfigCreate(
            name="override_test_agent",
            agent_type="analyst",
            role="analyst",
            prompt_template="Original prompt",
            capabilities=["market_analysis"],
            is_reserved=False,
            is_active=True,
        )

        agent = await agent_service.create_agent(agent_data)
        agent_id = agent.id

        # Update it
        update_data = AgentConfigUpdate(
            prompt_template="Updated prompt via override",
        )

        updated_agent = await agent_service.update_agent(agent_id, update_data)
        assert updated_agent is not None

        # Verify the plugin was overridden
        registry = get_agent_registry()
        plugin = registry.get_plugin("override_test_agent")
        assert plugin is not None
        assert plugin.prompt_template == "Updated prompt via override"

    async def test_hot_reload_does_not_override_reserved_agents(
        self,
        agent_service: AgentConfigService,
    ):
        """Test that custom agents cannot override reserved built-in agents."""
        # Try to create a custom agent with same name as built-in
        # This should fail at the service level, but if it somehow gets to DB,
        # hot-reload should skip it
        agent = AgentConfig(
            name="market_analyst",  # Same as built-in
            agent_type="analyst",
            role="analyst",
            prompt_template="Fake market analyst",
            capabilities_json=json.dumps(["market_analysis"]),
            is_reserved=False,  # Not reserved
            is_active=True,
        )
        
        agent_service.session.add(agent)
        await agent_service.session.commit()

        # Trigger hot-reload
        registry = get_agent_registry()
        await agent_service._trigger_hot_reload()

        # Verify built-in agent was not overridden
        plugin = registry.get_plugin("market_analyst")
        assert plugin is not None
        assert plugin.is_reserved
        # Should still be the original built-in, not the fake one
        # Note: This test assumes the custom agent with conflicting name is skipped
