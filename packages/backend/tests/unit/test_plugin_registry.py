"""Unit tests for plugin registry."""

import pytest

from tradingagents.plugins import (
    DataVendorPlugin,
    PluginCapability,
    VendorPluginRegistry,
    get_registry,
    initialize_registry,
)
from tradingagents.plugins.vendors import (
    AlphaVantagePlugin,
    GooglePlugin,
    LocalPlugin,
    OpenAIPlugin,
    YFinancePlugin,
)


@pytest.mark.unit
class TestPluginRegistry:
    """Test the plugin registry functionality."""

    def test_initialize_registry(self):
        """Test registry initialization."""
        registry = initialize_registry()
        
        assert isinstance(registry, VendorPluginRegistry)
        plugins = registry.list_plugins()
        assert len(plugins) > 0

    def test_list_plugins(self):
        """Test listing all plugins."""
        registry = initialize_registry()
        plugins = registry.list_plugins()
        
        plugin_names = [p.name for p in plugins]
        assert "yfinance" in plugin_names
        assert "alpha_vantage" in plugin_names
        assert "local" in plugin_names

    def test_get_plugin_by_name(self):
        """Test retrieving a plugin by name."""
        registry = initialize_registry()
        
        yfinance = registry.get_plugin("yfinance")
        assert yfinance is not None
        assert yfinance.name == "yfinance"
        assert isinstance(yfinance, YFinancePlugin)

    def test_get_nonexistent_plugin(self):
        """Test retrieving a non-existent plugin returns None."""
        registry = initialize_registry()
        
        plugin = registry.get_plugin("nonexistent")
        assert plugin is None

    def test_get_plugins_with_capability(self):
        """Test filtering plugins by capability."""
        registry = initialize_registry()
        
        stock_plugins = registry.get_plugins_with_capability(PluginCapability.STOCK_DATA)
        assert len(stock_plugins) > 0
        
        for plugin in stock_plugins:
            assert PluginCapability.STOCK_DATA in plugin.capabilities

    def test_register_plugin(self):
        """Test registering a new plugin."""
        registry = VendorPluginRegistry()
        
        class TestPlugin(DataVendorPlugin):
            name = "test"
            provider = "test"
            capabilities = [PluginCapability.STOCK_DATA]
            
            async def fetch_stock_price(self, ticker, date):
                return {}
        
        test_plugin = TestPlugin()
        registry.register(test_plugin)
        
        retrieved = registry.get_plugin("test")
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_duplicate_plugin_registration(self):
        """Test that duplicate plugin registration is handled."""
        registry = VendorPluginRegistry()
        
        class TestPlugin(DataVendorPlugin):
            name = "test"
            provider = "test"
            capabilities = [PluginCapability.STOCK_DATA]
            
            async def fetch_stock_price(self, ticker, date):
                return {}
        
        test_plugin1 = TestPlugin()
        test_plugin2 = TestPlugin()
        
        registry.register(test_plugin1)
        registry.register(test_plugin2)
        
        plugins = registry.list_plugins()
        test_plugins = [p for p in plugins if p.name == "test"]
        assert len(test_plugins) == 1

    def test_singleton_registry(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        assert registry1 is registry2

    def test_plugin_capabilities(self):
        """Test that plugins have correct capabilities."""
        registry = initialize_registry()
        
        yfinance = registry.get_plugin("yfinance")
        assert PluginCapability.STOCK_DATA in yfinance.capabilities
        assert PluginCapability.INDICATORS in yfinance.capabilities
        
        alpha_vantage = registry.get_plugin("alpha_vantage")
        assert PluginCapability.STOCK_DATA in alpha_vantage.capabilities
        assert PluginCapability.FUNDAMENTALS in alpha_vantage.capabilities
        assert PluginCapability.NEWS in alpha_vantage.capabilities


@pytest.mark.unit
class TestPluginCapabilities:
    """Test plugin capability enumeration."""

    def test_all_capabilities_defined(self):
        """Test that all expected capabilities are defined."""
        capabilities = [
            PluginCapability.STOCK_DATA,
            PluginCapability.INDICATORS,
            PluginCapability.FUNDAMENTALS,
            PluginCapability.NEWS,
            PluginCapability.BALANCE_SHEET,
            PluginCapability.CASHFLOW,
        ]
        
        for cap in capabilities:
            assert isinstance(cap, PluginCapability)

    def test_capability_uniqueness(self):
        """Test that each capability has a unique value."""
        capabilities = list(PluginCapability)
        values = [cap.value for cap in capabilities]
        
        assert len(values) == len(set(values))


@pytest.mark.unit
class TestVendorPlugins:
    """Test individual vendor plugins."""

    def test_yfinance_plugin(self):
        """Test YFinance plugin properties."""
        plugin = YFinancePlugin()
        
        assert plugin.name == "yfinance"
        assert plugin.provider == "Yahoo Finance"
        assert len(plugin.capabilities) > 0

    def test_alpha_vantage_plugin(self):
        """Test Alpha Vantage plugin properties."""
        plugin = AlphaVantagePlugin()
        
        assert plugin.name == "alpha_vantage"
        assert plugin.provider == "Alpha Vantage"
        assert len(plugin.capabilities) > 0

    def test_local_plugin(self):
        """Test Local plugin properties."""
        plugin = LocalPlugin()
        
        assert plugin.name == "local"
        assert plugin.provider == "Local Data"
        assert len(plugin.capabilities) > 0

    def test_openai_plugin(self):
        """Test OpenAI plugin properties."""
        plugin = OpenAIPlugin()
        
        assert plugin.name == "openai"
        assert plugin.provider == "OpenAI"
        assert len(plugin.capabilities) > 0

    def test_google_plugin(self):
        """Test Google plugin properties."""
        plugin = GooglePlugin()
        
        assert plugin.name == "google"
        assert plugin.provider == "Google"
        assert len(plugin.capabilities) > 0
