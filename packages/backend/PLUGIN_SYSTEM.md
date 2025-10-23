# Data Vendor Plugin System

This document describes the plugin-based architecture for data vendors in TradingAgents.

## Overview

The plugin system provides a flexible, extensible architecture for integrating data vendors. It supports:

- **Plugin Discovery**: Automatic discovery of built-in and third-party plugins
- **Dynamic Configuration**: Hot-reloadable configuration via YAML/JSON or API
- **Fallback Routing**: Automatic fallback to alternative vendors on failure
- **Rate Limiting**: Per-vendor rate limit configuration
- **FastAPI Admin**: REST API for managing vendors and configuration

## Architecture

### Core Components

1. **DataVendorPlugin** (`tradingagents/plugins/base.py`)
   - Abstract base class that all vendor plugins must implement
   - Defines common interface for data retrieval methods
   - Provides capability system for advertising supported operations

2. **VendorPluginRegistry** (`tradingagents/plugins/registry.py`)
   - Singleton registry for discovering and managing plugins
   - Supports entry point-based plugin discovery
   - Handles plugin registration and lifecycle

3. **VendorConfigManager** (`tradingagents/plugins/config_manager.py`)
   - Manages vendor configuration with hot-reload support
   - Loads from YAML/JSON files
   - Provides configuration persistence

4. **Router** (`tradingagents/plugins/router.py`)
   - Routes data requests to appropriate vendor plugins
   - Implements fallback logic with automatic retries
   - Handles error recovery and rate limiting

## Built-in Plugins

The system includes five built-in plugins:

1. **YFinancePlugin** - Yahoo Finance data
2. **AlphaVantagePlugin** - Alpha Vantage API
3. **LocalPlugin** - Local/cached data sources (Finnhub, SimFin, Reddit)
4. **OpenAIPlugin** - OpenAI-powered analysis
5. **GooglePlugin** - Google News

## Creating a Custom Plugin

### 1. Implement the Plugin Class

```python
from typing import List
from tradingagents.plugins.base import DataVendorPlugin, PluginCapability


class MyVendorPlugin(DataVendorPlugin):
    @property
    def name(self) -> str:
        return "my_vendor"
    
    @property
    def provider(self) -> str:
        return "my_vendor"
    
    @property
    def capabilities(self) -> List[PluginCapability]:
        return [
            PluginCapability.STOCK_DATA,
            PluginCapability.NEWS,
        ]
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
        # Implement your data retrieval logic
        return "stock data"
    
    def get_news(self, symbol: str = None, limit: int = 10) -> str:
        # Implement your news retrieval logic
        return "news data"
```

### 2. Register the Plugin

**Option A: Programmatic Registration**

```python
from tradingagents.plugins import get_registry

registry = get_registry()
registry.register_plugin(MyVendorPlugin, config={
    "rate_limit_per_minute": 60,
    "api_key": "your-key-here"
})
```

**Option B: Entry Points (setuptools)**

In your `setup.py` or `pyproject.toml`:

```python
entry_points={
    'tradingagents.plugins': [
        'my_vendor = mypackage.plugins:MyVendorPlugin',
    ],
}
```

## Configuration

### File-based Configuration

Create a `vendor_config.yaml` or `vendor_config.json` file:

```yaml
vendors:
  my_vendor:
    rate_limit_per_minute: 60
    api_key_ref: "MY_VENDOR_API_KEY"
    enabled: true

routing:
  get_stock_data:
    - my_vendor
    - yfinance
    - local
```

Load the configuration:

```python
from pathlib import Path
from tradingagents.plugins.config_manager import get_config_manager

config_manager = get_config_manager(
    config_file=Path("vendor_config.yaml")
)
```

### API-based Configuration

Use the FastAPI admin endpoints:

```bash
# List all vendors
curl http://localhost:8000/vendors/

# Get vendor details
curl http://localhost:8000/vendors/yfinance

# Update vendor configuration
curl -X PUT http://localhost:8000/vendors/yfinance/config \
  -H "Content-Type: application/json" \
  -d '{"config": {"rate_limit_per_minute": 30}}'

# Update routing configuration
curl -X PUT http://localhost:8000/vendors/routing/config \
  -H "Content-Type: application/json" \
  -d '{"method": "get_stock_data", "vendors": ["alpha_vantage", "yfinance"]}'

# Reload configuration from file
curl -X POST http://localhost:8000/vendors/config/reload
```

## API Endpoints

### Vendor Management

- `GET /vendors/` - List all registered plugins
- `GET /vendors/{vendor_name}` - Get plugin details
- `GET /vendors/{vendor_name}/config` - Get vendor configuration
- `PUT /vendors/{vendor_name}/config` - Update vendor configuration
- `GET /vendors/capabilities/{capability}` - Get vendors by capability

### Routing Configuration

- `GET /vendors/routing/config` - Get all routing configuration
- `GET /vendors/routing/config/{method}` - Get routing for specific method
- `PUT /vendors/routing/config` - Update routing configuration

### Hot Reload

- `POST /vendors/config/reload` - Reload configuration from file

## Capabilities

The system defines the following capabilities:

- `STOCK_DATA` - OHLCV stock price data
- `INDICATORS` - Technical indicators
- `FUNDAMENTALS` - Company fundamental data
- `BALANCE_SHEET` - Balance sheet data
- `CASHFLOW` - Cash flow statements
- `INCOME_STATEMENT` - Income statements
- `NEWS` - Company news
- `GLOBAL_NEWS` - Market/global news
- `INSIDER_SENTIMENT` - Insider sentiment data
- `INSIDER_TRANSACTIONS` - Insider transaction data

## Routing and Fallback

The router automatically handles:

1. **Priority-based Selection**: Vendors are tried in configured order
2. **Automatic Fallback**: On failure, next vendor is tried automatically
3. **Rate Limit Handling**: Special handling for rate limit errors
4. **Error Recovery**: Graceful degradation with detailed logging

### Example Routing Flow

For `get_stock_data` with routing `["yfinance", "alpha_vantage", "local"]`:

1. Try `yfinance` first
2. If it fails → try `alpha_vantage`
3. If it fails → try `local`
4. If all fail → raise error

## Hot Reload

Configuration can be reloaded without restarting:

```python
from tradingagents.plugins.config_manager import get_config_manager

config_manager = get_config_manager()
config_manager.reload()
```

Or via API:

```bash
curl -X POST http://localhost:8000/vendors/config/reload
```

## Usage in Agent Tools

All agent tools automatically route through the plugin system:

```python
from tradingagents.agents.utils.core_stock_tools import get_stock_data

# Automatically uses configured vendors with fallback
result = get_stock_data(symbol="AAPL", start_date="2024-01-01", end_date="2024-12-31")
```

## Migration from Legacy System

The system maintains backward compatibility:

1. **Legacy routing still works** - Old configuration is respected
2. **Plugin routing takes precedence** - If plugins are available, they're used
3. **Gradual migration** - Can migrate vendors one at a time

## Best Practices

1. **Configure Rate Limits**: Set appropriate rate limits for each vendor
2. **Order by Reliability**: Put most reliable vendors first in routing
3. **Use Hot Reload**: Update configuration without downtime
4. **Monitor Logs**: Check logs for fallback patterns and failures
5. **Test Fallbacks**: Ensure fallback chain covers failure scenarios

## Troubleshooting

### Plugin Not Found

Check if plugin is registered:

```python
from tradingagents.plugins import get_registry

registry = get_registry()
print(registry.list_plugin_names())
```

### Configuration Not Loading

Check file path and format:

```python
from tradingagents.plugins.config_manager import get_config_manager

config_manager = get_config_manager()
print(config_manager.to_dict())
```

### Vendor Always Failing Over

Check vendor implementation and credentials:

```python
from tradingagents.plugins import get_registry

registry = get_registry()
plugin = registry.get_plugin("vendor_name")
print(plugin.capabilities)
```

## Examples

See example configuration files:
- `vendor_config.example.yaml`
- `vendor_config.example.json`

## Future Enhancements

Potential future improvements:

1. Plugin versioning and compatibility checks
2. Async/await support for concurrent vendor calls
3. Circuit breaker pattern for failing vendors
4. Caching layer for vendor responses
5. Metrics and monitoring integration
6. A/B testing for vendor performance
7. Dynamic plugin loading from external packages
