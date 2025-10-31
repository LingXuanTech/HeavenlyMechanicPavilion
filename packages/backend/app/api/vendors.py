"""API endpoints for vendor plugin management."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.vendor import (
    AllRoutingConfigResponse,
    ConfigReloadResponse,
    RoutingConfigResponse,
    RoutingConfigUpdate,
    VendorCapabilitiesResponse,
    VendorConfigResponse,
    VendorConfigUpdate,
    VendorPluginInfo,
    VendorPluginList,
)
from tradingagents.plugins import get_registry
from tradingagents.plugins.config_manager import get_config_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=VendorPluginList)
async def list_vendors():
    """List all registered vendor plugins."""
    try:
        registry = get_registry()
        plugins = registry.list_plugins()

        plugin_infos = []
        for plugin in plugins:
            plugin_info = VendorPluginInfo(
                name=plugin.name,
                provider=plugin.provider,
                description=plugin.description,
                version=plugin.version,
                priority=plugin.priority,
                capabilities=[cap.value for cap in plugin.capabilities],
                rate_limits=plugin.get_rate_limits(),
                is_active=True,
            )
            plugin_infos.append(plugin_info)

        return VendorPluginList(plugins=plugin_infos, count=len(plugin_infos))
    except Exception as e:
        logger.error(f"Failed to list vendors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_name}", response_model=VendorPluginInfo)
async def get_vendor(vendor_name: str):
    """Get information about a specific vendor plugin."""
    try:
        registry = get_registry()
        plugin = registry.get_plugin(vendor_name)

        if not plugin:
            raise HTTPException(status_code=404, detail=f"Vendor '{vendor_name}' not found")

        return VendorPluginInfo(
            name=plugin.name,
            provider=plugin.provider,
            description=plugin.description,
            version=plugin.version,
            priority=plugin.priority,
            capabilities=[cap.value for cap in plugin.capabilities],
            rate_limits=plugin.get_rate_limits(),
            is_active=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get vendor {vendor_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_name}/config", response_model=VendorConfigResponse)
async def get_vendor_config(vendor_name: str):
    """Get configuration for a specific vendor."""
    try:
        config_manager = get_config_manager()
        config = config_manager.get_vendor_config(vendor_name)

        return VendorConfigResponse(vendor_name=vendor_name, config=config)
    except Exception as e:
        logger.error(f"Failed to get vendor config for {vendor_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{vendor_name}/config", response_model=VendorConfigResponse)
async def update_vendor_config(vendor_name: str, update: VendorConfigUpdate):
    """Update configuration for a specific vendor."""
    try:
        registry = get_registry()
        plugin = registry.get_plugin(vendor_name)

        if not plugin:
            raise HTTPException(status_code=404, detail=f"Vendor '{vendor_name}' not found")

        config_manager = get_config_manager()
        config_manager.set_vendor_config(vendor_name, update.config)

        # Update the plugin with new configuration
        registry.update_plugin_config(vendor_name, update.config)

        # Optionally save to file
        try:
            config_manager.save_config()
        except Exception as e:
            logger.warning(f"Failed to save config to file: {e}")

        return VendorConfigResponse(vendor_name=vendor_name, config=update.config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update vendor config for {vendor_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities/{capability}", response_model=VendorCapabilitiesResponse)
async def get_vendors_by_capability(capability: str):
    """Get all vendors that support a specific capability."""
    try:
        from tradingagents.plugins.base import PluginCapability

        # Validate capability
        try:
            cap_enum = PluginCapability(capability)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability. Valid options: {[c.value for c in PluginCapability]}",
            )

        registry = get_registry()
        plugins = registry.get_plugins_with_capability(cap_enum)

        vendor_names = [plugin.name for plugin in plugins]

        return VendorCapabilitiesResponse(capability=capability, vendors=vendor_names)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get vendors by capability {capability}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing/config", response_model=AllRoutingConfigResponse)
async def get_routing_config():
    """Get all routing configuration."""
    try:
        config_manager = get_config_manager()
        routing = config_manager.get_all_routing_config()

        return AllRoutingConfigResponse(routing=routing)
    except Exception as e:
        logger.error(f"Failed to get routing config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing/config/{method}", response_model=RoutingConfigResponse)
async def get_method_routing_config(method: str):
    """Get routing configuration for a specific method."""
    try:
        config_manager = get_config_manager()
        vendors = config_manager.get_routing_config(method)

        return RoutingConfigResponse(method=method, vendors=vendors)
    except Exception as e:
        logger.error(f"Failed to get routing config for {method}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/routing/config", response_model=RoutingConfigResponse)
async def update_routing_config(update: RoutingConfigUpdate):
    """Update routing configuration for a method."""
    try:
        config_manager = get_config_manager()
        config_manager.set_routing_config(update.method, update.vendors)

        # Optionally save to file
        try:
            config_manager.save_config()
        except Exception as e:
            logger.warning(f"Failed to save config to file: {e}")

        return RoutingConfigResponse(method=update.method, vendors=update.vendors)
    except Exception as e:
        logger.error(f"Failed to update routing config for {update.method}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/reload", response_model=ConfigReloadResponse)
async def reload_config():
    """Reload configuration from file."""
    try:
        config_manager = get_config_manager()
        success = config_manager.reload()

        last_reload = config_manager.get_last_reload()

        if success:
            message = "Configuration reloaded successfully with changes"
        else:
            message = "Configuration reloaded, no changes detected"

        return ConfigReloadResponse(success=True, message=message, last_reload=last_reload)
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        return ConfigReloadResponse(
            success=False, message=f"Failed to reload configuration: {e}", last_reload=None
        )
