"""Dynamic agent plugin loaded from database configuration."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .plugin_base import AgentCapability, AgentPlugin, AgentRole

logger = logging.getLogger(__name__)


class DatabaseAgentPlugin(AgentPlugin):
    """Agent plugin dynamically loaded from database configuration.
    
    This plugin wraps database-stored agent configurations and conforms
    to the AgentPlugin interface, allowing custom agents to be loaded
    at runtime without code changes.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the database agent plugin.
        
        Args:
            config: Plugin configuration containing:
                - name: Agent name
                - role: Agent role (from AgentRole enum)
                - capabilities: List of capabilities (from AgentCapability enum)
                - prompt_template: Agent prompt template
                - description: Optional agent description
                - version: Optional version string
                - requires_memory: Optional memory requirement flag
                - memory_name: Optional memory identifier
                - required_tools: Optional list of tool names
                - llm_type: Optional LLM type ('quick' or 'deep')
                - is_reserved: Optional reserved flag (default False for DB agents)
                - slot_name: Optional workflow slot name
                - metadata: Optional additional metadata
        """
        if not config:
            raise ValueError("DatabaseAgentPlugin requires configuration")
        
        # Validate required fields
        required_fields = ["name", "role", "capabilities", "prompt_template"]
        missing_fields = [f for f in required_fields if f not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        super().__init__(config)
        
        # Parse role from string to enum
        try:
            self._role = AgentRole(config["role"])
        except ValueError as e:
            raise ValueError(f"Invalid role '{config['role']}': {e}")
        
        # Parse capabilities from strings to enums
        try:
            self._capabilities = [AgentCapability(cap) for cap in config["capabilities"]]
        except ValueError as e:
            raise ValueError(f"Invalid capability in list: {e}")

    @property
    def name(self) -> str:
        return self.config["name"]

    @property
    def role(self) -> AgentRole:
        return self._role

    @property
    def capabilities(self) -> List[AgentCapability]:
        return self._capabilities

    @property
    def prompt_template(self) -> str:
        return self.config["prompt_template"]

    @property
    def description(self) -> str:
        return self.config.get("description", f"{self.name} agent")

    @property
    def version(self) -> str:
        return self.config.get("version", "1.0.0")

    @property
    def requires_memory(self) -> bool:
        return self.config.get("requires_memory", False)

    @property
    def memory_name(self) -> Optional[str]:
        return self.config.get("memory_name")

    @property
    def required_tools(self) -> List[str]:
        return self.config.get("required_tools", [])

    @property
    def llm_type(self) -> str:
        return self.config.get("llm_type", "quick")

    @property
    def is_reserved(self) -> bool:
        # Database agents are never reserved by default
        return self.config.get("is_reserved", False)

    @property
    def slot_name(self) -> Optional[str]:
        return self.config.get("slot_name")

    def create_node(self, llm: BaseChatModel, memory: Optional[Any] = None, **kwargs) -> Callable:
        """Create a generic agent node function for database-defined agents.
        
        This creates a basic node that uses the configured prompt template
        and available tools. Since database agents don't have custom logic,
        we provide a generic implementation that follows the standard pattern.
        
        Args:
            llm: The language model to use
            memory: Optional memory instance for the agent
            **kwargs: Additional arguments (e.g., tools registry)
        
        Returns:
            Callable: The agent node function
        """
        # Get tools from kwargs if provided
        tools = kwargs.get("tools", [])
        
        def database_agent_node(state):
            """Generic node function for database-configured agents."""
            current_date = state.get("trade_date", "")
            ticker = state.get("company_of_interest", "")
            
            system_message = self.prompt_template
            
            # Build base system message
            base_system = (
                "You are a helpful AI assistant, collaborating with other assistants."
                " Use the provided tools to progress towards answering the question."
                " If you are unable to fully answer, that's OK; another assistant with different tools"
                " will help where you left off. Execute what you can to make progress."
                " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
            )
            
            if tools:
                base_system += " You have access to the following tools: {tool_names}."
            
            base_system += "\n{system_message}"
            
            if current_date:
                base_system += "\nFor your reference, the current date is {current_date}."
            if ticker:
                base_system += " The company we want to look at is {ticker}."
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", base_system),
                MessagesPlaceholder(variable_name="messages"),
            ])
            
            prompt = prompt.partial(system_message=system_message)
            
            if tools:
                prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
                chain = prompt | llm.bind_tools(tools)
            else:
                chain = prompt | llm
            
            if current_date:
                prompt = prompt.partial(current_date=current_date)
            if ticker:
                prompt = prompt.partial(ticker=ticker)
            
            result = chain.invoke(state["messages"])
            
            # Return messages as required by the workflow
            return {
                "messages": [result],
            }
        
        return database_agent_node


def create_plugin_from_db_config(db_config: Any) -> Optional[DatabaseAgentPlugin]:
    """Create a DatabaseAgentPlugin from a database AgentConfig model.
    
    Args:
        db_config: AgentConfig model instance from database
    
    Returns:
        DatabaseAgentPlugin instance or None if config is malformed
    """
    try:
        # Deserialize JSON fields
        llm_config = {}
        if db_config.llm_config_json:
            try:
                llm_config = json.loads(db_config.llm_config_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid llm_config_json for agent {db_config.name}: {e}")
        
        capabilities = []
        if db_config.capabilities_json:
            try:
                capabilities = json.loads(db_config.capabilities_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid capabilities_json for agent {db_config.name}: {e}")
                return None
        
        required_tools = []
        if db_config.required_tools_json:
            try:
                required_tools = json.loads(db_config.required_tools_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid required_tools_json for agent {db_config.name}: {e}")
        
        agent_config = {}
        if db_config.config_json:
            try:
                agent_config = json.loads(db_config.config_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid config_json for agent {db_config.name}: {e}")
        
        metadata = {}
        if db_config.metadata_json:
            try:
                metadata = json.loads(db_config.metadata_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid metadata_json for agent {db_config.name}: {e}")
        
        # Build plugin config
        plugin_config = {
            "name": db_config.name,
            "role": db_config.role,
            "capabilities": capabilities,
            "prompt_template": db_config.prompt_template,
            "description": db_config.description,
            "version": db_config.version,
            "requires_memory": db_config.requires_memory,
            "memory_name": db_config.memory_name,
            "required_tools": required_tools,
            "is_reserved": db_config.is_reserved,
            "slot_name": db_config.slot_name,
            "llm_config": llm_config,
            "agent_config": agent_config,
            "metadata": metadata,
        }
        
        return DatabaseAgentPlugin(config=plugin_config)
    
    except Exception as e:
        logger.error(f"Failed to create plugin from database config {db_config.name}: {e}")
        return None
