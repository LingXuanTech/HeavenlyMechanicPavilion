# Agent Plugin System

This document describes the pluggable agent architecture and configurable LangGraph orchestration in TradingAgents.

## Overview

The agent plugin system provides a flexible, extensible architecture for defining and managing trading agents. It supports:

- **Plugin-based Architecture**: All agents conform to the `AgentPlugin` base class
- **Dynamic Configuration**: Agent configurations stored in database with hot-reload support
- **Reserved and Custom Agents**: Core workflow agents are reserved, custom agents can be added
- **Workflow Slots**: Configurable slots for analysts (market, social, news, fundamentals)
- **Memory Management**: Agents can specify memory requirements
- **Tool Requirements**: Agents declare required tools
- **CRUD APIs**: FastAPI endpoints for managing agent configurations

## Architecture

### Core Components

1. **AgentPlugin** (`tradingagents/agents/plugin_base.py`)
   - Abstract base class that all agent plugins must implement
   - Defines interface for prompts, memory, tools, and node creation
   - Provides metadata for registration and discovery

2. **AgentPluginRegistry** (`tradingagents/agents/plugin_registry.py`)
   - Singleton registry for managing agent plugins
   - Supports registration, retrieval, and filtering by role/capability
   - Handles slot assignments for analyst agents

3. **Built-in Plugins** (`tradingagents/agents/plugins/`)
   - 12 built-in agent plugin implementations
   - Analysts: Market, Social, News, Fundamentals
   - Researchers: Bull, Bear
   - Managers: Research Manager, Risk Manager
   - Trader: Single trader agent
   - Risk Analysts: Risky, Safe, Neutral

4. **Database Persistence** (`app/db/models/agent_config.py`)
   - `AgentConfig` model stores agent configurations
   - Fields for prompts, capabilities, tools, memory, slots
   - Supports versioning and active/inactive status

5. **API Endpoints** (`app/api/agents.py`)
   - REST API for CRUD operations on agents
   - Hot-reload endpoint for dynamic updates
   - Filtering and pagination support

## Agent Roles and Capabilities

### AgentRole Enum

- `ANALYST`: Market data analysis agents
- `RESEARCHER`: Investment research agents (bull/bear)
- `MANAGER`: Decision-making managers
- `TRADER`: Trading decision agents
- `RISK_ANALYST`: Risk analysis agents
- `RISK_MANAGER`: Final risk management

### AgentCapability Enum

- `MARKET_ANALYSIS`: Technical analysis and indicators
- `SOCIAL_SENTIMENT`: Social media sentiment analysis
- `NEWS_ANALYSIS`: News and macroeconomic analysis
- `FUNDAMENTAL_ANALYSIS`: Financial statements analysis
- `BULL_RESEARCH`: Bullish investment cases
- `BEAR_RESEARCH`: Bearish investment cases
- `INVESTMENT_MANAGEMENT`: Portfolio management decisions
- `RISK_MANAGEMENT`: Risk assessment and mitigation
- `TRADING`: Final trading decisions
- `RISKY_ANALYSIS`: High-risk perspectives
- `NEUTRAL_ANALYSIS`: Balanced risk perspectives
- `SAFE_ANALYSIS`: Conservative risk perspectives

## Creating a Custom Agent Plugin

### 1. Implement the Plugin Class

```python
from typing import Any, Callable, List, Optional
from langchain_core.language_models import BaseChatModel
from tradingagents.agents.plugin_base import AgentPlugin, AgentRole, AgentCapability


class MyCustomAnalyst(AgentPlugin):
    """Custom analyst for specialized analysis."""
    
    @property
    def name(self) -> str:
        return "my_custom_analyst"
    
    @property
    def role(self) -> AgentRole:
        return AgentRole.ANALYST
    
    @property
    def capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.MARKET_ANALYSIS]
    
    @property
    def prompt_template(self) -> str:
        return """You are a custom analyst. Your task is to..."""
    
    @property
    def description(self) -> str:
        return "Custom analyst for specialized market analysis"
    
    @property
    def required_tools(self) -> List[str]:
        return ["get_stock_data"]
    
    @property
    def llm_type(self) -> str:
        return "quick"
    
    @property
    def slot_name(self) -> Optional[str]:
        return "custom"  # or None for non-analyst agents
    
    @property
    def is_reserved(self) -> bool:
        return False  # Custom agents are not reserved
    
    def create_node(
        self,
        llm: BaseChatModel,
        memory: Optional[Any] = None,
        **kwargs
    ) -> Callable:
        """Create the agent node function."""
        def my_analyst_node(state):
            # Implement your agent logic here
            # Access state fields: state["trade_date"], state["company_of_interest"], etc.
            
            # Use tools if needed
            from tradingagents.agents.utils.agent_utils import get_stock_data
            tools = [get_stock_data]
            
            # Create prompt and invoke LLM
            prompt = f"Analyze {state['company_of_interest']}..."
            response = llm.invoke(prompt)
            
            # Return state updates
            return {
                "messages": [response],
                "custom_report": response.content,
            }
        
        return my_analyst_node
```

### 2. Register the Plugin

**Option A: Programmatic Registration**

```python
from tradingagents.agents import get_agent_registry

registry = get_agent_registry()
registry.register_plugin(MyCustomAnalyst)
```

**Option B: Entry Points (setuptools)**

In your `setup.py` or `pyproject.toml`:

```python
entry_points={
    'tradingagents.agent_plugins': [
        'my_custom = mypackage.agents:MyCustomAnalyst',
    ],
}
```

### 3. Add to Database (Optional)

Use the API to persist the agent configuration:

```bash
curl -X POST http://localhost:8000/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_custom_analyst",
    "agent_type": "analyst",
    "role": "analyst",
    "description": "Custom analyst for specialized analysis",
    "llm_type": "quick",
    "prompt_template": "You are a custom analyst...",
    "capabilities": ["market_analysis"],
    "required_tools": ["get_stock_data"],
    "is_reserved": false,
    "slot_name": "custom",
    "is_active": true
  }'
```

## API Endpoints

### Agent Management

- `GET /agents/` - List all agents (supports filtering)
  - Query params: `role`, `is_active`, `skip`, `limit`
- `GET /agents/{agent_id}` - Get agent by ID
- `GET /agents/by-name/{agent_name}` - Get agent by name
- `POST /agents/` - Create new agent
- `PUT /agents/{agent_id}` - Update agent
- `DELETE /agents/{agent_id}` - Delete agent (fails for reserved agents)
- `POST /agents/{agent_id}/activate` - Activate agent
- `POST /agents/{agent_id}/deactivate` - Deactivate agent
- `POST /agents/reload` - Hot-reload agent registry

### Example API Usage

```bash
# List all agents
curl http://localhost:8000/agents/

# Get specific agent
curl http://localhost:8000/agents/1

# Get agent by name
curl http://localhost:8000/agents/by-name/market_analyst

# Filter by role
curl http://localhost:8000/agents/?role=analyst

# Update agent prompt
curl -X PUT http://localhost:8000/agents/1 \
  -H "Content-Type: application/json" \
  -d '{"prompt_template": "New prompt template..."}'

# Deactivate agent
curl -X POST http://localhost:8000/agents/1/deactivate

# Hot-reload registry
curl -X POST http://localhost:8000/agents/reload
```

## Database Schema

The `agent_configs` table stores agent configurations:

```sql
CREATE TABLE agent_configs (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    
    -- LLM Configuration
    llm_provider VARCHAR(50) DEFAULT 'openai',
    llm_model VARCHAR(100) DEFAULT 'gpt-4o-mini',
    llm_type VARCHAR(20) DEFAULT 'quick',
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER,
    
    -- Agent Configuration
    prompt_template TEXT,
    capabilities_json TEXT,
    required_tools_json TEXT,
    
    -- Memory Configuration
    requires_memory BOOLEAN DEFAULT false,
    memory_name VARCHAR(100),
    
    -- Workflow Configuration
    is_reserved BOOLEAN DEFAULT true,
    slot_name VARCHAR(50),
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT '1.0.0',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Additional
    description VARCHAR(1000),
    config_json TEXT,
    metadata_json TEXT,
    
    -- Indexes
    INDEX idx_agent_type (agent_type),
    INDEX idx_role (role),
    INDEX idx_slot_name (slot_name),
    INDEX idx_is_active (is_active)
);
```

## Hot Reload

The system supports hot-reload of agent configurations without restarting:

1. **Trigger**: Call `POST /agents/reload` endpoint
2. **Process**:
   - Clear current agent registry
   - Re-register built-in plugins
   - Load custom agents from database
   - Update graph configuration
3. **Limitations**:
   - Active graph executions continue with old configuration
   - New executions use updated configuration

## Graph Construction from Registry

The `TradingAgentsGraph` class supports plugin-based construction:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

# Use plugin system
graph = TradingAgentsGraph(
    selected_analysts=["market", "social", "news", "fundamentals"],
    config=my_config,
    use_plugin_system=True,  # Enable plugin system
)

# Registry is automatically initialized and populated
# Agents are loaded from registry instead of factory functions
```

## Reserved Agents

Reserved agents are part of the core workflow and cannot be deleted:

1. **Analysts** (4 reserved slots):
   - Market Analyst
   - Social Analyst
   - News Analyst
   - Fundamentals Analyst

2. **Researchers** (2 required):
   - Bull Researcher
   - Bear Researcher

3. **Managers** (2 required):
   - Research Manager
   - Risk Manager

4. **Trader** (1 required):
   - Trader

5. **Risk Analysts** (3 required):
   - Risky Analyst
   - Safe Analyst
   - Neutral Analyst

## Workflow Slots

Analyst agents occupy workflow slots that determine their position in the analysis pipeline:

- **market**: Market/technical analysis
- **social**: Social media sentiment
- **news**: News and macroeconomics
- **fundamentals**: Financial fundamentals

Custom analysts can occupy custom slots or replace default slots.

## Best Practices

1. **Naming Conventions**: Use snake_case for agent names
2. **Prompt Templates**: Keep prompts focused and specific
3. **Tool Requirements**: Only declare tools the agent actually uses
4. **Memory Usage**: Enable memory only for agents that need reflection
5. **Reserved Flag**: Only set `is_reserved=True` for core workflow agents
6. **Version Control**: Increment version when making significant changes
7. **Testing**: Test agent nodes independently before integration

## Migration Guide

### From Legacy to Plugin System

1. **Identify Agents**: List all agents in your workflow
2. **Create Plugins**: Implement `AgentPlugin` for each
3. **Register**: Add plugins to registry
4. **Update Graph**: Enable `use_plugin_system=True`
5. **Test**: Verify workflow execution
6. **Migrate Database**: Run Alembic migrations

### Backward Compatibility

The system maintains backward compatibility:
- Legacy factory functions still work
- Plugin system is opt-in via `use_plugin_system` flag
- Existing graphs continue to function

## Troubleshooting

### Plugin Not Found

Check if plugin is registered:

```python
from tradingagents.agents import get_agent_registry

registry = get_agent_registry()
print(registry.list_plugin_names())
```

### Agent Not Loading

Verify database configuration:

```bash
curl http://localhost:8000/agents/by-name/my_agent
```

### Hot-Reload Not Working

Check service logs for errors:

```bash
curl -X POST http://localhost:8000/agents/reload
# Check logs for "Agent registry reloaded successfully"
```

## Future Enhancements

Potential improvements:

1. Dynamic agent loading from external packages
2. Agent versioning and compatibility checks
3. Agent performance metrics and monitoring
4. A/B testing for agent configurations
5. Agent composition and chaining
6. Conditional agent activation based on market conditions
7. Agent marketplace for sharing custom agents

## Examples

See `tradingagents/agents/plugins/` for complete examples of all 12 built-in agents.
