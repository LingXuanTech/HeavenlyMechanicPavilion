"""Plugin system for data vendors."""

from .base import DataVendorPlugin, PluginCapability
from .registry import VendorPluginRegistry, get_registry, initialize_registry
from .router import route_to_vendor

__all__ = [
    "DataVendorPlugin",
    "PluginCapability",
    "VendorPluginRegistry",
    "get_registry",
    "initialize_registry",
    "route_to_vendor",
]
