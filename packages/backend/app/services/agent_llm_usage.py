"""Service helpers for agent LLM usage analytics."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.agent_llm_usage import AgentLLMUsage
from ..repositories.agent_llm_usage import AgentLLMUsageRepository
from ..schemas.agent_llm_usage import (
    AgentLLMUsageQuery,
    AgentLLMUsageRecord,
    AgentLLMUsageSummary,
)


class AgentLLMUsageService:
    """Business logic for reading/writing LLM usage metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = AgentLLMUsageRepository(session)

    async def record_usage(
        self,
        *,
        agent_id: int,
        provider: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        is_fallback: bool = False,
        metadata: Optional[dict] = None,
        occurred_at: Optional[datetime] = None,
    ) -> AgentLLMUsageRecord:
        usage = AgentLLMUsage(
            agent_id=agent_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            is_fallback=is_fallback,
            created_at=occurred_at or datetime.utcnow(),
            metadata_json=json.dumps(metadata) if metadata else None,
        )

        created = await self._repository.create(usage)
        return AgentLLMUsageRecord(
            id=created.id,
            agent_id=created.agent_id,
            provider=created.provider,
            model_name=created.model_name,
            is_fallback=created.is_fallback,
            prompt_tokens=created.prompt_tokens,
            completion_tokens=created.completion_tokens,
            total_tokens=created.total_tokens,
            cost_usd=created.cost_usd,
            created_at=created.created_at,
            metadata=metadata,
        )

    async def get_usage(
        self,
        agent_id: int,
        query: Optional[AgentLLMUsageQuery] = None,
    ) -> AgentLLMUsageSummary:
        query = query or AgentLLMUsageQuery()
        records = await self._repository.list_by_agent(
            agent_id,
            start=query.start,
            end=query.end,
            limit=query.limit,
        )

        serialized_records = []
        total_prompt = 0
        total_completion = 0
        total_tokens = 0
        total_cost = 0.0

        for record in records:
            metadata = None
            if record.metadata_json:
                try:
                    metadata = json.loads(record.metadata_json)
                except json.JSONDecodeError:
                    metadata = None

            serialized_records.append(
                AgentLLMUsageRecord(
                    id=record.id,
                    agent_id=record.agent_id,
                    provider=record.provider,
                    model_name=record.model_name,
                    is_fallback=record.is_fallback,
                    prompt_tokens=record.prompt_tokens,
                    completion_tokens=record.completion_tokens,
                    total_tokens=record.total_tokens,
                    cost_usd=record.cost_usd,
                    created_at=record.created_at,
                    metadata=metadata,
                )
            )

            total_prompt += record.prompt_tokens
            total_completion += record.completion_tokens
            total_tokens += record.total_tokens
            total_cost += record.cost_usd

        return AgentLLMUsageSummary(
            agent_id=agent_id,
            total_calls=len(records),
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            records=serialized_records,
        )
