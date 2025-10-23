#!/usr/bin/env python
"""Test script to verify the plugin system works correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_plugin_imports():
    """Test that plugin modules can be imported."""
    print("Testing plugin imports...")
    
    try:
        from tradingagents.plugins import (
            DataVendorPlugin,
            PluginCapability,
            VendorPluginRegistry,
            get_registry,
            initialize_registry,
            route_to_vendor,
        )
        print("✓ Core plugin modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import core plugin modules: {e}")
        return False
    
    try:
        from tradingagents.plugins.vendors import (
            YFinancePlugin,
            AlphaVantagePlugin,
            LocalPlugin,
            OpenAIPlugin,
            GooglePlugin,
        )
        print("✓ Vendor plugin modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import vendor plugin modules: {e}")
        return False
    
    return True


def test_plugin_registry():
    """Test the plugin registry functionality."""
    print("\nTesting plugin registry...")
    
    try:
        from tradingagents.plugins import initialize_registry, get_registry
        
        # Initialize registry
        registry = initialize_registry()
        print(f"✓ Registry initialized with {len(registry.list_plugins())} plugins")
        
        # List plugins
        plugins = registry.list_plugins()
        for plugin in plugins:
            print(f"  - {plugin.name} ({plugin.provider}): {len(plugin.capabilities)} capabilities")
        
        # Test getting specific plugins
        yfinance = registry.get_plugin("yfinance")
        if yfinance:
            print(f"✓ Retrieved yfinance plugin: {yfinance.description}")
        else:
            print("✗ Failed to retrieve yfinance plugin")
            return False
        
        # Test capability filtering
        from tradingagents.plugins.base import PluginCapability
        stock_plugins = registry.get_plugins_with_capability(PluginCapability.STOCK_DATA)
        print(f"✓ Found {len(stock_plugins)} plugins with STOCK_DATA capability")
        
        return True
    except Exception as e:
        print(f"✗ Registry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager():
    """Test the configuration manager."""
    print("\nTesting configuration manager...")
    
    try:
        from tradingagents.plugins.config_manager import get_config_manager
        
        # Get config manager without file (uses defaults)
        config_manager = get_config_manager()
        print("✓ Config manager initialized")
        
        # Test getting routing config
        routing = config_manager.get_all_routing_config()
        print(f"✓ Retrieved routing config with {len(routing)} methods")
        
        # Test getting vendor config
        vendor_config = config_manager.get_vendor_config("yfinance")
        print(f"✓ Retrieved vendor config: {vendor_config}")
        
        return True
    except Exception as e:
        print(f"✗ Config manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_schemas():
    """Test that API schemas can be imported."""
    print("\nTesting API schemas...")
    
    try:
        from app.schemas.vendor import (
            VendorPluginInfo,
            VendorPluginList,
            VendorConfigUpdate,
            RoutingConfigUpdate,
        )
        print("✓ API schemas imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import API schemas: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_interface_integration():
    """Test that interface.py integrates with plugin system."""
    print("\nTesting interface integration...")
    
    try:
        from tradingagents.dataflows.interface import route_to_vendor
        print("✓ Interface route_to_vendor imported successfully")
        print("  Note: Full integration test requires API keys and network access")
        return True
    except Exception as e:
        print(f"✗ Failed to import from interface: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Plugin System Test Suite")
    print("=" * 60)
    
    tests = [
        test_plugin_imports,
        test_plugin_registry,
        test_config_manager,
        test_api_schemas,
        test_interface_integration,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
