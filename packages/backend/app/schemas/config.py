"""Schemas describing TradingAgents configuration payloads."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class GraphConfiguration(BaseModel):
    llm_provider: Optional[str] = None
    deep_think_llm: Optional[str] = None
    quick_think_llm: Optional[str] = None
    results_dir: Optional[str] = None
    data_vendors: Dict[str, str] = Field(default_factory=dict)
    tool_vendors: Dict[str, str] = Field(default_factory=dict)
