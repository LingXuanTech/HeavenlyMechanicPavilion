"""Usage tracking helpers for LLM invocations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult


@dataclass
class LLMUsageRecord:
    """Represents a single LLM invocation for monitoring."""

    agent_id: Optional[int]
    agent_name: str
    provider: str
    model: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    cost: Optional[float]
    latency_ms: Optional[float]
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class LLMUsageTracker:
    """Collects usage records during a workflow run."""

    def __init__(self) -> None:
        self._records: List[LLMUsageRecord] = []

    @property
    def records(self) -> List[LLMUsageRecord]:
        return self._records

    def record(self, record: LLMUsageRecord) -> None:
        self._records.append(record)

    def record_failure(
        self,
        *,
        agent_id: Optional[int],
        agent_name: str,
        provider: str,
        model: str,
        error: Exception,
    ) -> None:
        """Record a failed invocation when callbacks are not triggered."""
        self._records.append(
            LLMUsageRecord(
                agent_id=agent_id,
                agent_name=agent_name,
                provider=provider,
                model=model,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                cost=None,
                latency_ms=None,
                success=False,
                error_type=error.__class__.__name__,
                error_message=str(error),
            )
        )


class LLMUsageCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler to capture token usage and latency."""

    def __init__(
        self,
        *,
        tracker: LLMUsageTracker,
        agent_id: Optional[int],
        agent_name: str,
        provider: str,
        model: str,
        cost_per_1k_tokens: Optional[float] = None,
    ) -> None:
        self._tracker = tracker
        self._agent_id = agent_id
        self._agent_name = agent_name
        self._provider = provider
        self._model = model
        self._cost_per_1k = cost_per_1k_tokens
        self._start: Optional[float] = None

    def on_llm_start(self, *args, **kwargs) -> None:  # type: ignore[override]
        self._start = time.perf_counter()

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:  # type: ignore[override]
        latency_ms: Optional[float] = None
        if self._start is not None:
            latency_ms = (time.perf_counter() - self._start) * 1000.0
        token_usage = {}
        if response.llm_output:
            token_usage = (
                response.llm_output.get("token_usage")
                or response.llm_output.get("usage")
                or response.llm_output.get("usage_metadata")
                or {}
            )
        prompt_tokens = token_usage.get("prompt_tokens") or token_usage.get("input_tokens")
        completion_tokens = token_usage.get("completion_tokens") or token_usage.get("output_tokens")
        total_tokens = token_usage.get("total_tokens")
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens
        cost = None
        if self._cost_per_1k is not None and total_tokens is not None:
            cost = (total_tokens / 1000.0) * self._cost_per_1k
        self._tracker.record(
            LLMUsageRecord(
                agent_id=self._agent_id,
                agent_name=self._agent_name,
                provider=self._provider,
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                success=True,
            )
        )
        self._start = None

    def on_llm_error(self, error: Exception, **kwargs) -> None:  # type: ignore[override]
        latency_ms: Optional[float] = None
        if self._start is not None:
            latency_ms = (time.perf_counter() - self._start) * 1000.0
        self._tracker.record(
            LLMUsageRecord(
                agent_id=self._agent_id,
                agent_name=self._agent_name,
                provider=self._provider,
                model=self._model,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                cost=None,
                latency_ms=latency_ms,
                success=False,
                error_type=error.__class__.__name__,
                error_message=str(error),
            )
        )
        self._start = None
