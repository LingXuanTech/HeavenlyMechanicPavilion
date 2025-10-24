"""Contract tests for configuration loaders."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from tradingagents.plugins.config_manager import VendorConfigManager, get_config_manager


@pytest.mark.unit
class TestConfigManager:
    """Test configuration manager functionality."""

    def test_default_config(self):
        """Test loading default configuration."""
        config_manager = VendorConfigManager()
        
        routing = config_manager.get_all_routing_config()
        assert isinstance(routing, dict)
        assert len(routing) > 0

    def test_get_routing_config(self):
        """Test getting routing configuration for specific method."""
        config_manager = VendorConfigManager()
        
        stock_vendors = config_manager.get_routing_config("get_stock_data")
        assert isinstance(stock_vendors, list)
        assert "yfinance" in stock_vendors or "alpha_vantage" in stock_vendors

    def test_get_vendor_config(self):
        """Test getting vendor-specific configuration."""
        config_manager = VendorConfigManager()
        
        vendor_config = config_manager.get_vendor_config("yfinance")
        assert isinstance(vendor_config, dict)

    def test_set_routing_config(self):
        """Test setting routing configuration."""
        config_manager = VendorConfigManager()
        
        config_manager.set_routing_config("get_stock_data", ["yfinance", "local"])
        updated_vendors = config_manager.get_routing_config("get_stock_data")
        
        assert updated_vendors == ["yfinance", "local"]

    def test_load_json_config(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "routing": {
                "get_stock_data": ["yfinance"],
                "get_indicators": ["yfinance"],
            },
            "vendors": {
                "yfinance": {
                    "enabled": True,
                    "timeout": 30,
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            config_manager = VendorConfigManager(config_path)
            
            routing = config_manager.get_all_routing_config()
            assert routing["get_stock_data"] == ["yfinance"]
            
            vendor_config = config_manager.get_vendor_config("yfinance")
            assert vendor_config.get("enabled") is True
            assert vendor_config.get("timeout") == 30
        finally:
            config_path.unlink()

    def test_load_yaml_config(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "routing": {
                "get_stock_data": ["alpha_vantage"],
                "get_news": ["google"],
            },
            "vendors": {
                "alpha_vantage": {
                    "api_key": "test_key",
                    "rate_limit": 5,
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            config_manager = VendorConfigManager(config_path)
            
            routing = config_manager.get_all_routing_config()
            assert routing["get_stock_data"] == ["alpha_vantage"]
            assert routing["get_news"] == ["google"]
            
            vendor_config = config_manager.get_vendor_config("alpha_vantage")
            assert vendor_config.get("rate_limit") == 5
        finally:
            config_path.unlink()

    def test_invalid_config_file(self):
        """Test handling of invalid configuration file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False
        ) as f:
            f.write("invalid json content {]")
            config_path = Path(f.name)
        
        try:
            config_manager = VendorConfigManager(config_path)
            routing = config_manager.get_all_routing_config()
            assert isinstance(routing, dict)
        finally:
            config_path.unlink()

    def test_nonexistent_config_file(self):
        """Test handling of non-existent configuration file."""
        config_manager = VendorConfigManager(Path("/nonexistent/path/config.json"))
        
        routing = config_manager.get_all_routing_config()
        assert isinstance(routing, dict)

    def test_reload_config(self):
        """Test configuration reloading."""
        config_manager = VendorConfigManager()
        
        result = config_manager.reload()
        assert isinstance(result, bool)

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config_manager = VendorConfigManager()
        
        config_dict = config_manager.to_dict()
        assert isinstance(config_dict, dict)
        assert "routing" in config_dict


@pytest.mark.unit
class TestConfigContracts:
    """Contract tests for configuration structure."""

    def test_routing_config_contract(self):
        """Test that routing config has expected structure."""
        config_manager = VendorConfigManager()
        routing = config_manager.get_all_routing_config()
        
        expected_methods = [
            "get_stock_data",
            "get_indicators",
            "get_fundamentals",
            "get_news",
        ]
        
        for method in expected_methods:
            assert method in routing

    def test_routing_config_returns_lists(self):
        """Test that routing config values are lists."""
        config_manager = VendorConfigManager()
        routing = config_manager.get_all_routing_config()
        
        for method, vendors in routing.items():
            assert isinstance(vendors, list)

    def test_vendor_config_contract(self):
        """Test that vendor config has expected structure."""
        config_manager = VendorConfigManager()
        
        vendors = ["yfinance", "alpha_vantage", "local"]
        
        for vendor in vendors:
            config = config_manager.get_vendor_config(vendor)
            assert isinstance(config, dict)

    def test_config_serialization(self):
        """Test configuration serialization."""
        config_manager = VendorConfigManager()
        
        routing = config_manager.get_all_routing_config()
        
        serialized = json.dumps(routing)
        deserialized = json.loads(serialized)
        
        assert deserialized == routing


@pytest.mark.unit
class TestGlobalConfigManager:
    """Test global config manager singleton."""

    def test_get_config_manager(self):
        """Test getting global config manager."""
        manager = get_config_manager()
        
        assert isinstance(manager, VendorConfigManager)

    def test_singleton_behavior(self):
        """Test that get_config_manager returns same instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
