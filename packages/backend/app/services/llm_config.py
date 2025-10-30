"""Service layer for managing agent-level LLM configuration and usage."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional
import time

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm import (
    AgentLLMOrchestrator,
    AgentLLMRuntimeConfig,
    LLMProviderFactory,
    LLMRuntimeBundle,
    LLMUsageRecord,
    LLMUsageTracker,
)

from ..db.models import AgentConfig, AgentLLMConfig, AgentLLMUsage
from ..repositories import (
    AgentConfigRepository,
    AgentLLMConfigRepository,
    AgentLLMUsageRepository,
)
from ..schemas.llm_config import (
    AgentLLMConfigCreate,
    AgentLLMConfigResponse,
    AgentLLMConfigUpdate,
    AgentLLMUsageRecord as AgentLLMUsageRecordSchema,
    AgentLLMUsageSummary,
)
from .crypto import decrypt_secret, encrypt_secret


DEFAULT_QUICK_TEMPERATURE = 0.7
DEFAULT_DEEP_TEMPERATURE = 0.5


class LLMConfigService:
    """Provides CRUD operations and runtime assembly for LLM configs."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_repo = AgentConfigRepository(session)
        self.llm_repo = AgentLLMConfigRepository(session)
        self.usage_repo = AgentLLMUsageRepository(session)
        self.provider_factory = LLMProviderFactory()

    async def get_agent_llm_config(self, agent_id: int) -> Optional[AgentLLMConfigResponse]:
        llm_config = await self.llm_repo.get_by_agent_id(agent_id)
        agent_config = await self.agent_repo.get(agent_id)
        if not agent_config and not llm_config:
            return None
        if llm_config:
            return self._to_response(llm_config, fallback_agent=agent_config)
        if agent_config:
            return self._from_agent_defaults(agent_config)
        return None

    async def upsert_agent_llm_config(
        self,
        agent_id: int,
        payload: AgentLLMConfigCreate | AgentLLMConfigUpdate,
    ) -> AgentLLMConfigResponse:
        existing = await self.llm_repo.get_by_agent_id(agent_id)
        now = datetime.utcnow()
        payload_dict = payload.model_dump(exclude_unset=True)
        api_key_plain = payload_dict.pop("api_key", None)
        api_key_encrypted: Optional[str]
        if api_key_plain is None:
            api_key_encrypted = existing.api_key_encrypted if existing else None
        elif api_key_plain == "":
            api_key_encrypted = None
        else:
            api_key_encrypted = encrypt_secret(api_key_plain)

        if existing:
            update_dict = {
                **payload_dict,
                "api_key_encrypted": api_key_encrypted,
                "updated_at": now,
            }
            updated = await self.llm_repo.update(db_obj=existing, obj_in=update_dict)
            await self.session.refresh(updated)
            return self._to_response(updated)

        create_dict = {
            **payload_dict,
            "agent_id": agent_id,
            "api_key_encrypted": api_key_encrypted,
            "created_at": now,
            "updated_at": now,
        }
        new_config = AgentLLMConfig(**create_dict)
        created = await self.llm_repo.create(new_config)
        await self.session.refresh(created)
        return self._to_response(created)

    async def remove_agent_llm_config(self, agent_id: int) -> bool:
        config = await self.llm_repo.get_by_agent_id(agent_id)
        if not config:
            return False
        return await self.llm_repo.delete(id=config.id)  # type: ignore[arg-type]

    async def record_usage_events(self, events: Iterable[LLMUsageRecord]) -> None:
        models = [
            AgentLLMUsage(
                agent_id=event.agent_id,
                agent_name=event.agent_name,
                provider=event.provider,
                model=event.model,
                prompt_tokens=event.prompt_tokens,
                completion_tokens=event.completion_tokens,
                total_tokens=event.total_tokens,
                cost=event.cost,
                latency_ms=event.latency_ms,
                success=event.success,
                error_type=event.error_type,
                error_message=event.error_message,
            )
            for event in events
        ]
        if models:
            await self.usage_repo.create_many(models)

    async def usage_summary(self, *, agent_id: Optional[int] = None, provider: Optional[str] = None) -> AgentLLMUsageSummary:
        totals = await self.usage_repo.aggregate_totals(agent_id=agent_id, provider=provider)
        return AgentLLMUsageSummary(**totals)

    async def recent_usage(
        self,
        *,
        agent_id: Optional[int] = None,
        provider: Optional[str] = None,
        window_hours: int = 24,
    ) -> List[AgentLLMUsageRecordSchema]:
        records = await self.usage_repo.recent_usage(agent_id=agent_id, provider=provider, window_hours=window_hours)
        return [AgentLLMUsageRecordSchema.model_validate(record) for record in records]

    async def build_runtime_bundle(self) -> LLMRuntimeBundle:
        defaults = self._default_runtime_configs()
        overrides: Dict[str, AgentLLMRuntimeConfig] = {}

        enabled_configs = await self.llm_repo.list_enabled()
        for config in enabled_configs:
            if not config.agent:
                continue
            agent = config.agent
            api_key = decrypt_secret(config.api_key_encrypted)
            overrides[agent.name] = AgentLLMRuntimeConfig(
                agent_id=agent.id,
                agent_name=agent.name,
                llm_type=agent.llm_type,
                provider=config.provider,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                api_key=api_key,
                fallback_provider=config.fallback_provider,
                fallback_model=config.fallback_model,
                cost_per_1k_tokens=config.cost_per_1k_tokens,
                enabled=config.enabled,
            )

        return LLMRuntimeBundle(defaults=defaults, agent_overrides=overrides)

    async def build_orchestrator(self) -> AgentLLMOrchestrator:
        bundle = await self.build_runtime_bundle()
        return AgentLLMOrchestrator(bundle, provider_factory=self.provider_factory, tracker=LLMUsageTracker())

    async def test_agent_llm(
        self,
        agent_id: int,
        *,
        prompt: Optional[str] = None,
    ) -> tuple[bool, str, Optional[float], Optional[str], Optional[str]]:
        agent = await self.agent_repo.get(agent_id)
        if not agent:
            raise ValueError(f"Agent with ID {agent_id} not found")

        orchestrator = await self.build_orchestrator()
        context = orchestrator.get_context(agent.name, agent.llm_type, agent_id=agent.id)
        message = prompt or "Hello from TradingAgents connectivity check."

        last_error: Optional[str] = None
        for runtime_config, model in context.iter_models():
            try:
                start = time.perf_counter()
                model.invoke([HumanMessage(content=message)])
                latency_ms = (time.perf_counter() - start) * 1000.0
                await self.record_usage_events(orchestrator.tracker.records)
                orchestrator.tracker.records.clear()
                return True, "LLM invocation succeeded", latency_ms, runtime_config.provider, runtime_config.model
            except Exception as exc:  # pragma: no cover - network errors, provider exceptions
                last_error = str(exc)
                continue

        await self.record_usage_events(orchestrator.tracker.records)
        orchestrator.tracker.records.clear()
        return False, last_error or "Unknown error", None, None, None

    def _default_runtime_configs(self) -> Dict[str, AgentLLMRuntimeConfig]:
        provider = DEFAULT_CONFIG.get("llm_provider", "openai")
        quick_model = DEFAULT_CONFIG.get("quick_think_llm", "gpt-4o")
        deep_model = DEFAULT_CONFIG.get("deep_think_llm", "gpt-4")
        defaults = {
            "quick": AgentLLMRuntimeConfig(
                agent_id=None,
                agent_name="__default_quick__",
                llm_type="quick",
                provider=provider,
                model=quick_model,
                temperature=DEFAULT_QUICK_TEMPERATURE,
                max_tokens=None,
                top_p=None,
                api_key=None,
                fallback_provider=None,
                fallback_model=None,
                cost_per_1k_tokens=None,
                enabled=True,
            ),
            "deep": AgentLLMRuntimeConfig(
                agent_id=None,
                agent_name="__default_deep__",
                llm_type="deep",
                provider=provider,
                model=deep_model,
                temperature=DEFAULT_DEEP_TEMPERATURE,
                max_tokens=None,
                top_p=None,
                api_key=None,
                fallback_provider=None,
                fallback_model=None,
                cost_per_1k_tokens=None,
                enabled=True,
            ),
        }
        return defaults

    def _from_agent_defaults(self, agent: AgentConfig) -> AgentLLMConfigResponse:
        return AgentLLMConfigResponse(
            agent_id=agent.id,
            provider=agent.llm_provider,
            model=agent.llm_model,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            top_p=None,
            fallback_provider=None,
            fallback_model=None,
            cost_per_1k_tokens=None,
            enabled=True,
            has_api_key=False,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )

    def _to_response(
        self,
        config: AgentLLMConfig,
        *,
        fallback_agent: Optional[AgentConfig] = None,
    ) -> AgentLLMConfigResponse:
        agent = config.agent or fallback_agent
        agent_id = agent.id if agent else config.agent_id
        return AgentLLMConfigResponse(
            agent_id=agent_id,
            provider=config.provider,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            fallback_provider=config.fallback_provider,
            fallback_model=config.fallback_model,
            cost_per_1k_tokens=config.cost_per_1k_tokens,
            enabled=config.enabled,
            has_api_key=bool(config.api_key_encrypted),
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
