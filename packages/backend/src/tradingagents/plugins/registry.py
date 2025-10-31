"""Registry for managing data vendor plugins."""

import importlib.metadata
import logging
from typing import Dict, List, Optional, Type

from .base import DataVendorPlugin, PluginCapability

logger = logging.getLogger(__name__)


class VendorPluginRegistry:
    """Registry for discovering and managing data vendor plugins."""

    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[str, DataVendorPlugin] = {}
        self._plugin_classes: Dict[str, Type[DataVendorPlugin]] = {}

    def register_plugin(
        self, plugin_class: Type[DataVendorPlugin], config: Optional[Dict] = None
    ) -> None:
        """Register a plugin class with optional configuration.

        Args:
            plugin_class: The plugin class to register
            config: Optional configuration for the plugin instance
        """
        try:
            plugin_instance = plugin_class(config=config)
            plugin_name = plugin_instance.name

            if plugin_name in self._plugins:
                logger.warning(f"Plugin '{plugin_name}' already registered, replacing")

            self._plugins[plugin_name] = plugin_instance
            self._plugin_classes[plugin_name] = plugin_class
            logger.info(f"Registered plugin: {plugin_name} (provider: {plugin_instance.provider})")

        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
            raise

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin by name.

        Args:
            plugin_name: Name of the plugin to unregister
        """
        if plugin_name in self._plugins:
            del self._plugins[plugin_name]
            if plugin_name in self._plugin_classes:
                del self._plugin_classes[plugin_name]
            logger.info(f"Unregistered plugin: {plugin_name}")
        else:
            logger.warning(f"Plugin '{plugin_name}' not found in registry")

    def get_plugin(self, plugin_name: str) -> Optional[DataVendorPlugin]:
        """Get a plugin instance by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(plugin_name)

    def get_plugin_by_provider(self, provider: str) -> Optional[DataVendorPlugin]:
        """Get a plugin instance by provider name.

        Args:
            provider: Provider name (e.g., 'yfinance', 'alpha_vantage')

        Returns:
            First plugin instance matching the provider or None if not found
        """
        for plugin in self._plugins.values():
            if plugin.provider == provider:
                return plugin
        return None

    def list_plugins(self) -> List[DataVendorPlugin]:
        """Get list of all registered plugins.

        Returns:
            List of plugin instances
        """
        return list(self._plugins.values())

    def list_plugin_names(self) -> List[str]:
        """Get list of all registered plugin names.

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())

    def get_plugins_with_capability(self, capability: PluginCapability) -> List[DataVendorPlugin]:
        """Get all plugins that support a specific capability.

        Args:
            capability: The capability to filter by

        Returns:
            List of plugins that support the capability
        """
        return [plugin for plugin in self._plugins.values() if plugin.supports(capability)]

    def discover_plugins(self) -> None:
        """Discover and load plugins using entry points.

        Looks for plugins registered under the 'tradingagents.plugins' entry point group.
        """
        try:
            entry_points = importlib.metadata.entry_points()

            # Handle different versions of importlib.metadata
            if hasattr(entry_points, "select"):
                # Python 3.10+
                plugin_entries = entry_points.select(group="tradingagents.plugins")
            else:
                # Python 3.9 and earlier
                plugin_entries = entry_points.get("tradingagents.plugins", [])

            for entry_point in plugin_entries:
                try:
                    plugin_class = entry_point.load()
                    if issubclass(plugin_class, DataVendorPlugin):
                        self.register_plugin(plugin_class)
                        logger.info(f"Discovered plugin via entry point: {entry_point.name}")
                    else:
                        logger.warning(
                            f"Entry point {entry_point.name} does not provide a DataVendorPlugin"
                        )
                except Exception as e:
                    logger.error(f"Failed to load plugin from entry point {entry_point.name}: {e}")

        except Exception as e:
            logger.warning(f"Failed to discover plugins via entry points: {e}")

    def update_plugin_config(self, plugin_name: str, config: Dict) -> None:
        """Update the configuration for a plugin and reinitialize it.

        Args:
            plugin_name: Name of the plugin
            config: New configuration dictionary
        """
        if plugin_name not in self._plugin_classes:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        plugin_class = self._plugin_classes[plugin_name]
        self.register_plugin(plugin_class, config=config)
        logger.info(f"Updated configuration for plugin: {plugin_name}")

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._plugin_classes.clear()
        logger.info("Cleared all plugins from registry")


# Global registry instance
_registry: Optional[VendorPluginRegistry] = None


def get_registry() -> VendorPluginRegistry:
    """Get the global plugin registry instance.

    Returns:
        The global VendorPluginRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = VendorPluginRegistry()
    return _registry


def initialize_registry() -> VendorPluginRegistry:
    """Initialize the global registry with built-in plugins.

    Returns:
        The initialized registry
    """
    registry = get_registry()

    # Import and register built-in plugins
    try:
        from .vendors import (
            AlphaVantagePlugin,
            GooglePlugin,
            LocalPlugin,
            OpenAIPlugin,
            YFinancePlugin,
        )

        registry.register_plugin(YFinancePlugin)
        registry.register_plugin(AlphaVantagePlugin)
        registry.register_plugin(LocalPlugin)
        registry.register_plugin(OpenAIPlugin)
        registry.register_plugin(GooglePlugin)

        logger.info("Initialized registry with built-in plugins")
    except Exception as e:
        logger.error(f"Failed to initialize built-in plugins: {e}")

    # Discover any additional plugins via entry points
    registry.discover_plugins()

    return registry
