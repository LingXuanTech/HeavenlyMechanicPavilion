"""Service layer for agent LLM configuration management.

This module provides backward compatibility by re-exporting the AgentLLMService
from agent_llm_service.py with the expected name AgentLLMConfigService.
"""

from __future__ import annotations

from .agent_llm_service import (
    AgentLLMConfigNotFoundError,
    AgentNotFoundError,
)
from .agent_llm_service import (
    AgentLLMService as AgentLLMConfigService,
)

__all__ = [
    "AgentLLMConfigService",
    "AgentNotFoundError",
    "AgentLLMConfigNotFoundError",
]
