"""Registry for managing agent plugins."""

import logging
from typing import Dict, List, Optional, Type

from .plugin_base import AgentCapability, AgentPlugin, AgentRole

logger = logging.getLogger(__name__)


class AgentPluginRegistry:
    """Registry for discovering and managing agent plugins.

    This registry manages the lifecycle of agent plugins, including
    registration, discovery, and retrieval.
    """

    _instance: Optional["AgentPluginRegistry"] = None

    def __init__(self):
        """Initialize the agent plugin registry."""
        self._plugins: Dict[str, AgentPlugin] = {}
        self._plugin_classes: Dict[str, Type[AgentPlugin]] = {}
        self._slot_assignments: Dict[str, str] = {}  # slot_name -> plugin_name

    @classmethod
    def get_instance(cls) -> "AgentPluginRegistry":
        """Get the singleton instance of the registry.

        Returns:
            AgentPluginRegistry: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_plugin(
        self,
        plugin_class: Type[AgentPlugin],
        config: Optional[Dict] = None,
        override: bool = False,
    ) -> AgentPlugin:
        """Register an agent plugin.

        Args:
            plugin_class: The agent plugin class to register
            config: Optional configuration for the plugin
            override: Whether to override existing plugin with same name

        Returns:
            AgentPlugin: The instantiated plugin

        Raises:
            ValueError: If plugin name conflicts with existing plugin (unless override=True)
        """
        plugin = plugin_class(config=config)
        plugin_name = plugin.name

        if plugin_name in self._plugins and not override:
            raise ValueError(
                f"Agent plugin '{plugin_name}' is already registered. "
                f"Use override=True to replace it."
            )

        self._plugins[plugin_name] = plugin
        self._plugin_classes[plugin_name] = plugin_class

        # Register slot assignment if applicable
        if plugin.slot_name:
            self._slot_assignments[plugin.slot_name] = plugin_name

        logger.info(
            f"Registered agent plugin: {plugin_name} "
            f"(role={plugin.role.value}, capabilities={[c.value for c in plugin.capabilities]})"
        )

        return plugin

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister an agent plugin.

        Args:
            plugin_name: Name of the plugin to unregister

        Raises:
            ValueError: If plugin is reserved (cannot be unregistered)
        """
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin '{plugin_name}' not found in registry")
            return

        plugin = self._plugins[plugin_name]
        if plugin.is_reserved:
            raise ValueError(f"Cannot unregister reserved plugin '{plugin_name}'")

        # Remove slot assignment
        if plugin.slot_name:
            self._slot_assignments.pop(plugin.slot_name, None)

        del self._plugins[plugin_name]
        del self._plugin_classes[plugin_name]

        logger.info(f"Unregistered agent plugin: {plugin_name}")

    def get_plugin(self, plugin_name: str) -> Optional[AgentPlugin]:
        """Get a plugin by name.

        Args:
            plugin_name: Name of the plugin to retrieve

        Returns:
            AgentPlugin: The plugin instance, or None if not found
        """
        return self._plugins.get(plugin_name)

    def get_plugin_by_slot(self, slot_name: str) -> Optional[AgentPlugin]:
        """Get a plugin assigned to a specific slot.

        Args:
            slot_name: Name of the slot (e.g., 'market', 'social')

        Returns:
            AgentPlugin: The plugin instance, or None if slot not assigned
        """
        plugin_name = self._slot_assignments.get(slot_name)
        if plugin_name:
            return self.get_plugin(plugin_name)
        return None

    def list_plugins(self) -> List[AgentPlugin]:
        """List all registered plugins.

        Returns:
            List[AgentPlugin]: List of all plugin instances
        """
        return list(self._plugins.values())

    def list_plugin_names(self) -> List[str]:
        """List names of all registered plugins.

        Returns:
            List[str]: List of plugin names
        """
        return list(self._plugins.keys())

    def get_plugins_by_role(self, role: AgentRole) -> List[AgentPlugin]:
        """Get all plugins with a specific role.

        Args:
            role: The role to filter by

        Returns:
            List[AgentPlugin]: List of plugins with the specified role
        """
        return [p for p in self._plugins.values() if p.role == role]

    def get_plugins_by_capability(self, capability: AgentCapability) -> List[AgentPlugin]:
        """Get all plugins with a specific capability.

        Args:
            capability: The capability to filter by

        Returns:
            List[AgentPlugin]: List of plugins with the specified capability
        """
        return [p for p in self._plugins.values() if p.supports_capability(capability)]

    def get_reserved_plugins(self) -> List[AgentPlugin]:
        """Get all reserved (system) plugins.

        Returns:
            List[AgentPlugin]: List of reserved plugins
        """
        return [p for p in self._plugins.values() if p.is_reserved]

    def get_custom_plugins(self) -> List[AgentPlugin]:
        """Get all custom (non-reserved) plugins.

        Returns:
            List[AgentPlugin]: List of custom plugins
        """
        return [p for p in self._plugins.values() if not p.is_reserved]

    def clear(self) -> None:
        """Clear all plugins from the registry.

        Note: This is primarily for testing purposes.
        """
        self._plugins.clear()
        self._plugin_classes.clear()
        self._slot_assignments.clear()
        logger.info("Cleared all agent plugins from registry")

    def discover_plugins(self) -> None:
        """Discover and register plugins from entry points.

        Looks for entry points in the 'tradingagents.agent_plugins' group.
        """
        try:
            from importlib.metadata import entry_points

            # Get entry points (syntax differs between Python versions)
            try:
                eps = entry_points(group="tradingagents.agent_plugins")
            except TypeError:
                # Python < 3.10
                eps = entry_points().get("tradingagents.agent_plugins", [])

            for ep in eps:
                try:
                    plugin_class = ep.load()
                    self.register_plugin(plugin_class)
                    logger.info(f"Discovered and registered plugin from entry point: {ep.name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin from entry point {ep.name}: {e}")
        except ImportError:
            logger.warning("importlib.metadata not available, skipping entry point discovery")


# Singleton accessor function
def get_agent_registry() -> AgentPluginRegistry:
    """Get the global agent plugin registry instance.

    Returns:
        AgentPluginRegistry: The singleton registry instance
    """
    return AgentPluginRegistry.get_instance()


def initialize_agent_registry() -> AgentPluginRegistry:
    """Initialize the agent registry and discover plugins.

    Returns:
        AgentPluginRegistry: The initialized registry
    """
    registry = get_agent_registry()
    registry.discover_plugins()
    return registry
