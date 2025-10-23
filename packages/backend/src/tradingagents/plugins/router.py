"""Router for dispatching data vendor calls through the plugin system."""

import logging
from typing import Any, List, Optional

from tradingagents.dataflows.alpha_vantage_common import AlphaVantageRateLimitError

from .base import PluginCapability
from .config_manager import get_config_manager
from .registry import get_registry

logger = logging.getLogger(__name__)


# Map method names to capabilities
METHOD_TO_CAPABILITY = {
    "get_stock_data": PluginCapability.STOCK_DATA,
    "get_indicators": PluginCapability.INDICATORS,
    "get_fundamentals": PluginCapability.FUNDAMENTALS,
    "get_balance_sheet": PluginCapability.BALANCE_SHEET,
    "get_cashflow": PluginCapability.CASHFLOW,
    "get_income_statement": PluginCapability.INCOME_STATEMENT,
    "get_news": PluginCapability.NEWS,
    "get_global_news": PluginCapability.GLOBAL_NEWS,
    "get_insider_sentiment": PluginCapability.INSIDER_SENTIMENT,
    "get_insider_transactions": PluginCapability.INSIDER_TRANSACTIONS,
}


def route_to_vendor(method: str, *args, **kwargs) -> str:
    """Route method calls to appropriate vendor plugin with fallback support.
    
    Args:
        method: The method name to call (e.g., 'get_stock_data')
        *args: Positional arguments for the method
        **kwargs: Keyword arguments for the method
        
    Returns:
        Result from the vendor plugin
        
    Raises:
        RuntimeError: If all vendor attempts fail
        ValueError: If method is not supported
    """
    if method not in METHOD_TO_CAPABILITY:
        raise ValueError(f"Method '{method}' not supported")
    
    capability = METHOD_TO_CAPABILITY[method]
    
    # Get routing configuration
    config_manager = get_config_manager()
    configured_vendors = config_manager.get_routing_config(method)
    
    # Get registry
    registry = get_registry()
    
    # Get all plugins with this capability
    capable_plugins = registry.get_plugins_with_capability(capability)
    
    # Build fallback vendor list
    fallback_vendors = []
    
    # Add configured vendors first
    for vendor_name in configured_vendors:
        plugin = registry.get_plugin(vendor_name)
        if plugin and plugin.supports(capability):
            fallback_vendors.append(plugin)
        elif plugin:
            logger.warning(
                f"Configured vendor '{vendor_name}' does not support {method}, skipping"
            )
    
    # Add remaining capable plugins as fallbacks
    for plugin in capable_plugins:
        if plugin not in fallback_vendors:
            fallback_vendors.append(plugin)
    
    if not fallback_vendors:
        raise RuntimeError(f"No vendors available for method '{method}'")
    
    # Log fallback ordering
    primary_str = " → ".join([p.name for p in fallback_vendors[:len(configured_vendors)]])
    fallback_str = " → ".join([p.name for p in fallback_vendors])
    logger.debug(f"{method} - Primary: [{primary_str}] | Full fallback order: [{fallback_str}]")
    
    # Track results and execution state
    results = []
    vendor_attempt_count = 0
    
    for plugin in fallback_vendors:
        vendor_attempt_count += 1
        is_primary = vendor_attempt_count <= len(configured_vendors)
        
        vendor_type = "PRIMARY" if is_primary else "FALLBACK"
        logger.debug(
            f"Attempting {vendor_type} vendor '{plugin.name}' for {method} "
            f"(attempt #{vendor_attempt_count})"
        )
        
        try:
            # Get the method from the plugin
            plugin_method = getattr(plugin, method)
            result = plugin_method(*args, **kwargs)
            
            if result:
                results.append(result)
                logger.info(f"SUCCESS: Vendor '{plugin.name}' succeeded for {method}")
                
                # Stop after first successful vendor if single-vendor config
                if len(configured_vendors) <= 1:
                    logger.debug(
                        f"Stopping after successful vendor '{plugin.name}' (single-vendor config)"
                    )
                    break
        
        except AlphaVantageRateLimitError as e:
            logger.warning(
                f"RATE_LIMIT: Alpha Vantage rate limit exceeded for {method}, "
                f"falling back to next vendor"
            )
            logger.debug(f"Rate limit details: {e}")
            continue
        
        except NotImplementedError as e:
            logger.debug(f"Vendor '{plugin.name}' does not implement {method}: {e}")
            continue
        
        except Exception as e:
            logger.warning(f"FAILED: Vendor '{plugin.name}' failed for {method}: {e}")
            continue
    
    # Final result summary
    if not results:
        logger.error(f"FAILURE: All {vendor_attempt_count} vendor attempts failed for {method}")
        raise RuntimeError(f"All vendor implementations failed for method '{method}'")
    else:
        logger.info(
            f"FINAL: Method '{method}' completed with {len(results)} result(s) "
            f"from {vendor_attempt_count} vendor attempt(s)"
        )
    
    # Return single result if only one, otherwise concatenate
    if len(results) == 1:
        return results[0]
    else:
        return '\n'.join(str(result) for result in results)
