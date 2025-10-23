"""Base class for agent plugins in the TradingAgents system."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from langchain_core.language_models import BaseChatModel


class AgentRole(str, Enum):
    """Roles that agents can fulfill in the trading workflow."""
    
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    MANAGER = "manager"
    TRADER = "trader"
    RISK_ANALYST = "risk_analyst"
    RISK_MANAGER = "risk_manager"


class AgentCapability(str, Enum):
    """Capabilities that an agent can provide."""
    
    MARKET_ANALYSIS = "market_analysis"
    SOCIAL_SENTIMENT = "social_sentiment"
    NEWS_ANALYSIS = "news_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    BULL_RESEARCH = "bull_research"
    BEAR_RESEARCH = "bear_research"
    INVESTMENT_MANAGEMENT = "investment_management"
    RISK_MANAGEMENT = "risk_management"
    TRADING = "trading"
    RISKY_ANALYSIS = "risky_analysis"
    NEUTRAL_ANALYSIS = "neutral_analysis"
    SAFE_ANALYSIS = "safe_analysis"


class AgentPlugin(ABC):
    """Abstract base class for agent plugins.
    
    Each agent plugin must implement this interface to integrate
    with the TradingAgents orchestration system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin with optional configuration.
        
        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config or {}
        self._validate_config()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the agent plugin."""
        pass
    
    @property
    @abstractmethod
    def role(self) -> AgentRole:
        """Return the role this agent fulfills."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[AgentCapability]:
        """Return list of capabilities this agent provides."""
        pass
    
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Return the prompt template for this agent."""
        pass
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the agent."""
        return f"{self.name} agent"
    
    @property
    def version(self) -> str:
        """Return the agent plugin version."""
        return "1.0.0"
    
    @property
    def requires_memory(self) -> bool:
        """Return whether this agent requires persistent memory."""
        return False
    
    @property
    def memory_name(self) -> Optional[str]:
        """Return the memory identifier for this agent."""
        return None
    
    @property
    def required_tools(self) -> List[str]:
        """Return list of tool names required by this agent.
        
        Returns:
            List of tool function names (e.g., ['get_stock_data', 'get_indicators'])
        """
        return []
    
    @property
    def llm_type(self) -> str:
        """Return the preferred LLM type for this agent.
        
        Returns:
            'quick' for quick_thinking_llm or 'deep' for deep_thinking_llm
        """
        return "quick"
    
    @property
    def is_reserved(self) -> bool:
        """Return whether this is a reserved system agent.
        
        Reserved agents are part of the core workflow and cannot be removed.
        """
        return True
    
    @property
    def slot_name(self) -> Optional[str]:
        """Return the workflow slot this agent occupies.
        
        For analysts, this would be 'market', 'social', 'news', or 'fundamentals'.
        For other roles, this is typically None (single slot per role).
        """
        return None
    
    def _validate_config(self) -> None:
        """Validate the plugin configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    def supports_capability(self, capability: AgentCapability) -> bool:
        """Check if this agent supports a given capability.
        
        Args:
            capability: The capability to check
            
        Returns:
            bool: True if the capability is supported
        """
        return capability in self.capabilities
    
    @abstractmethod
    def create_node(
        self,
        llm: BaseChatModel,
        memory: Optional[Any] = None,
        **kwargs
    ) -> Callable:
        """Create the agent node function.
        
        Args:
            llm: The language model to use
            memory: Optional memory instance for the agent
            **kwargs: Additional arguments for node creation
            
        Returns:
            Callable: The agent node function that processes state
        """
        pass
    
    def get_conditional_logic(self) -> Optional[str]:
        """Return the name of conditional logic function for this agent.
        
        Returns:
            Name of the function in ConditionalLogic class, or None if no conditional routing
        """
        return None
    
    def get_tools_node_name(self) -> Optional[str]:
        """Return the name of the tools node for this agent.
        
        Returns:
            Name of the tools node (e.g., 'tools_market'), or None if no tools
        """
        return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return agent metadata for storage/display.
        
        Returns:
            Dictionary containing agent metadata
        """
        return {
            "name": self.name,
            "role": self.role.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "description": self.description,
            "version": self.version,
            "requires_memory": self.requires_memory,
            "memory_name": self.memory_name,
            "required_tools": self.required_tools,
            "llm_type": self.llm_type,
            "is_reserved": self.is_reserved,
            "slot_name": self.slot_name,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent configuration to dictionary for persistence.
        
        Returns:
            Dictionary containing full agent configuration
        """
        return {
            **self.get_metadata(),
            "prompt_template": self.prompt_template,
            "config": self.config,
        }
