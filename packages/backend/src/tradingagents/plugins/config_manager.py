"""Configuration manager for vendor plugins with hot-reload support."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class VendorConfigManager:
    """Manages vendor plugin configuration with hot-reload support."""

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize the config manager.

        Args:
            config_file: Optional path to configuration file (YAML/JSON)
        """
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._last_reload: Optional[datetime] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file if available."""
        if self.config_file and self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    if self.config_file.suffix in [".yaml", ".yml"]:
                        if not YAML_AVAILABLE:
                            raise ImportError("PyYAML is required to load YAML configuration files")
                        self._config = yaml.safe_load(f) or {}
                    elif self.config_file.suffix == ".json":
                        self._config = json.load(f)
                    else:
                        logger.warning(f"Unsupported config file format: {self.config_file.suffix}")
                        self._config = {}

                self._last_reload = datetime.utcnow()
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load configuration from {self.config_file}: {e}")
                self._config = {}
        else:
            self._config = self._get_default_config()
            logger.info("Using default configuration")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration structure."""
        return {
            "vendors": {},
            "routing": {
                "get_stock_data": ["yfinance", "alpha_vantage", "local"],
                "get_indicators": ["yfinance", "alpha_vantage", "local"],
                "get_fundamentals": ["alpha_vantage", "openai"],
                "get_balance_sheet": ["alpha_vantage", "yfinance", "local"],
                "get_cashflow": ["alpha_vantage", "yfinance", "local"],
                "get_income_statement": ["alpha_vantage", "yfinance", "local"],
                "get_news": ["alpha_vantage", "google", "openai", "local"],
                "get_global_news": ["openai", "local"],
                "get_insider_sentiment": ["local"],
                "get_insider_transactions": ["alpha_vantage", "yfinance", "local"],
            },
        }

    def reload(self) -> bool:
        """Reload configuration from file.

        Returns:
            True if reload was successful, False otherwise
        """
        try:
            old_config = self._config.copy()
            self._load_config()

            if old_config != self._config:
                logger.info("Configuration reloaded with changes")
                return True
            else:
                logger.info("Configuration reloaded, no changes detected")
                return False
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False

    def get_vendor_config(self, vendor_name: str) -> Dict[str, Any]:
        """Get configuration for a specific vendor.

        Args:
            vendor_name: Name of the vendor

        Returns:
            Vendor configuration dictionary
        """
        return self._config.get("vendors", {}).get(vendor_name, {})

    def set_vendor_config(self, vendor_name: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific vendor.

        Args:
            vendor_name: Name of the vendor
            config: Configuration dictionary
        """
        if "vendors" not in self._config:
            self._config["vendors"] = {}
        self._config["vendors"][vendor_name] = config
        logger.info(f"Updated configuration for vendor: {vendor_name}")

    def get_routing_config(self, method: str) -> List[str]:
        """Get vendor priority list for a method.

        Args:
            method: Method name (e.g., 'get_stock_data')

        Returns:
            List of vendor names in priority order
        """
        return self._config.get("routing", {}).get(method, [])

    def set_routing_config(self, method: str, vendors: List[str]) -> None:
        """Set vendor priority list for a method.

        Args:
            method: Method name
            vendors: List of vendor names in priority order
        """
        if "routing" not in self._config:
            self._config["routing"] = {}
        self._config["routing"][method] = vendors
        logger.info(f"Updated routing configuration for method: {method}")

    def get_all_routing_config(self) -> Dict[str, List[str]]:
        """Get all routing configuration.

        Returns:
            Dictionary mapping methods to vendor priority lists
        """
        return self._config.get("routing", {})

    def save_config(self) -> None:
        """Save current configuration to file."""
        if not self.config_file:
            logger.warning("No config file specified, cannot save")
            return

        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w") as f:
                if self.config_file.suffix in [".yaml", ".yml"]:
                    if not YAML_AVAILABLE:
                        raise ImportError("PyYAML is required to save YAML configuration files")
                    yaml.safe_dump(self._config, f, default_flow_style=False)
                elif self.config_file.suffix == ".json":
                    json.dump(self._config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_file.suffix}")

            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def get_last_reload(self) -> Optional[datetime]:
        """Get timestamp of last configuration reload.

        Returns:
            Datetime of last reload or None if never reloaded
        """
        return self._last_reload

    def to_dict(self) -> Dict[str, Any]:
        """Get current configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config.copy()


# Global config manager instance
_config_manager: Optional[VendorConfigManager] = None


def get_config_manager(config_file: Optional[Path] = None) -> VendorConfigManager:
    """Get the global config manager instance.

    Args:
        config_file: Optional path to configuration file

    Returns:
        The global VendorConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = VendorConfigManager(config_file=config_file)
    return _config_manager
