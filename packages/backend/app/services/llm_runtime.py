"""Runtime management for agent-specific LLM providers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableSerializable
from sqlalchemy import func, select

from tradingagents.llm_providers import ProviderFactory, ProviderType, get_model_info

from ..db import AgentConfig, AgentLLMConfig, get_db_manager
from ..security.encryption import decrypt_api_key
from .agent_llm_usage import AgentLLMUsageService

logger = logging.getLogger(__name__)

_API_KEY_ENV_ALIASES: Dict[str, str] = {
    "claude": "ANTHROPIC_API_KEY",
}


@dataclass
class _LLMClientInfo:
    provider: str
    model_name: str
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    temperature: float
    max_tokens: Optional[int]
    top_p: Optional[float]
    metadata: Dict[str, Any]


class AgentLLMUsageRecorder:
    """Persist usage metrics from synchronous execution contexts."""

    def __init__(self) -> None:
        self._db_manager = get_db_manager()

    def record(
        self,
        *,
        agent_id: int,
        info: _LLMClientInfo,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        is_fallback: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        cost = (
            (prompt_tokens / 1000.0) * info.cost_per_1k_input_tokens
            + (completion_tokens / 1000.0) * info.cost_per_1k_output_tokens
        )

        payload = {
            "agent_id": agent_id,
            "provider": info.provider,
            "model_name": info.model_name,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "cost_usd": float(cost),
            "is_fallback": is_fallback,
            "metadata": metadata,
        }

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self._record_async(payload))
        else:
            asyncio.run(self._record_async(payload))

    async def _record_async(self, payload: Dict[str, Any]) -> None:
        async for session in self._db_manager.get_session():
            try:
                service = AgentLLMUsageService(session)
                await service.record_usage(**payload)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to record LLM usage: %s", exc)
            finally:
                break


class _FallbackWrapper(RunnableSerializable):
    """Wraps a runnable to flag fallback usage before execution."""

    def __init__(self, flag: ContextVar[bool], runnable: RunnableSerializable) -> None:
        self._flag = flag
        self._runnable = runnable

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        self._flag.set(True)
        return self._runnable.invoke(input, config=config, **kwargs)

    async def ainvoke(self, input: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        self._flag.set(True)
        return await self._runnable.ainvoke(input, config=config, **kwargs)

    def batch(self, inputs: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        self._flag.set(True)
        return self._runnable.batch(inputs, config=config, **kwargs)

    async def abatch(self, inputs: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        self._flag.set(True)
        return await self._runnable.abatch(inputs, config=config, **kwargs)

    def stream(self, input: Any, config: Optional[dict] = None, **kwargs: Any):
        self._flag.set(True)
        yield from self._runnable.stream(input, config=config, **kwargs)

    async def astream(self, input: Any, config: Optional[dict] = None, **kwargs: Any):
        self._flag.set(True)
        async for chunk in self._runnable.astream(input, config=config, **kwargs):
            yield chunk


class ManagedLLM(RunnableSerializable):
    """Runnable wrapper adding fallback handling and usage recording."""

    def __init__(
        self,
        *,
        agent_id: int,
        agent_name: str,
        primary: RunnableSerializable,
        primary_info: _LLMClientInfo,
        usage_recorder: Optional[AgentLLMUsageRecorder] = None,
        fallback: Optional[RunnableSerializable] = None,
        fallback_info: Optional[_LLMClientInfo] = None,
    ) -> None:
        self._agent_id = agent_id
        self._agent_name = agent_name
        self._primary = primary
        self._primary_info = primary_info
        self._usage_recorder = usage_recorder
        self._fallback_info = fallback_info

        self._fallback_flag: ContextVar[bool] = ContextVar("fallback_used", default=False)

        if fallback and fallback_info:
            self._fallback_runnable = fallback
            fallback_wrapper = _FallbackWrapper(self._fallback_flag, fallback)
            self._delegate = self._primary.with_fallbacks([fallback_wrapper])
        else:
            self._fallback_runnable = None
            self._delegate = self._primary

    # ------------------------------------------------------------------
    def _extract_usage(self, result: Any) -> Dict[str, Any]:
        metadata = getattr(result, "response_metadata", {}) or {}
        token_usage = metadata.get("token_usage") or metadata.get("usage") or {}
        prompt = token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0
        completion = token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0
        total = token_usage.get("total_tokens") or (prompt + completion)
        return {
            "prompt": int(prompt or 0),
            "completion": int(completion or 0),
            "total": int(total or 0),
            "metadata": metadata,
        }

    def _record_usage(self, usage: Dict[str, Any], fallback_used: bool) -> None:
        if not self._usage_recorder:
            return

        info = self._fallback_info if fallback_used and self._fallback_info else self._primary_info
        metadata = {
            "agent_name": self._agent_name,
            "provider": info.provider,
            "model": info.model_name,
            "fallback_used": fallback_used,
            "response_metadata": usage["metadata"],
        }
        self._usage_recorder.record(
            agent_id=self._agent_id,
            info=info,
            prompt_tokens=usage["prompt"],
            completion_tokens=usage["completion"],
            total_tokens=usage["total"],
            is_fallback=fallback_used,
            metadata=metadata,
        )

    def _log_call(self, usage: Dict[str, Any], fallback_used: bool) -> None:
        info = self._fallback_info if fallback_used and self._fallback_info else self._primary_info
        logger.info(
            "agent_llm_call",
            extra={
                "agent_id": self._agent_id,
                "agent_name": self._agent_name,
                "provider": info.provider,
                "model": info.model_name,
                "fallback_used": fallback_used,
                "prompt_tokens": usage["prompt"],
                "completion_tokens": usage["completion"],
                "total_tokens": usage["total"],
            },
        )

    def _run(self, method: str, *args: Any, **kwargs: Any) -> Any:
        token = self._fallback_flag.set(False)
        try:
            result = getattr(self._delegate, method)(*args, **kwargs)
            fallback_used = self._fallback_flag.get()
        finally:
            self._fallback_flag.reset(token)

        usage = self._extract_usage(result)
        self._log_call(usage, fallback_used)
        self._record_usage(usage, fallback_used)
        return result

    async def _run_async(self, method: str, *args: Any, **kwargs: Any) -> Any:
        token = self._fallback_flag.set(False)
        try:
            result = await getattr(self._delegate, method)(*args, **kwargs)
            fallback_used = self._fallback_flag.get()
        finally:
            self._fallback_flag.reset(token)

        usage = self._extract_usage(result)
        self._log_call(usage, fallback_used)
        self._record_usage(usage, fallback_used)
        return result

    # RunnableSerializable ----------------------------------------------------
    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        return self._run("invoke", input, config=config, **kwargs)

    async def ainvoke(self, input: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        return await self._run_async("ainvoke", input, config=config, **kwargs)

    def batch(self, inputs: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        return self._run("batch", inputs, config=config, **kwargs)

    async def abatch(self, inputs: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        return await self._run_async("abatch", inputs, config=config, **kwargs)

    def stream(self, input: Any, config: Optional[dict] = None, **kwargs: Any):
        token = self._fallback_flag.set(False)
        try:
            yield from self._delegate.stream(input, config=config, **kwargs)
        finally:
            self._fallback_flag.reset(token)

    async def astream(self, input: Any, config: Optional[dict] = None, **kwargs: Any):
        token = self._fallback_flag.set(False)
        try:
            async for chunk in self._delegate.astream(input, config=config, **kwargs):
                yield chunk
        finally:
            self._fallback_flag.reset(token)

    def bind_tools(self, tools: Any) -> "ManagedLLM":
        primary = self._primary.bind_tools(tools)
        fallback = self._fallback_runnable.bind_tools(tools) if self._fallback_runnable else None
        return ManagedLLM(
            agent_id=self._agent_id,
            agent_name=self._agent_name,
            primary=primary,
            primary_info=self._primary_info,
            usage_recorder=self._usage_recorder,
            fallback=fallback,
            fallback_info=self._fallback_info,
        )


class AgentLLMRuntime:
    """Loads agent-specific LLM configuration and provides ManagedLLM instances."""

    def __init__(self, base_config: Dict[str, Any]) -> None:
        self._base_config = base_config
        self._db_manager = get_db_manager()
        self._usage_recorder = AgentLLMUsageRecorder()
        self._lock = threading.RLock()

        self._signature: Optional[tuple] = None
        self._agents: Dict[str, AgentConfig] = {}
        self._llm_configs: Dict[int, AgentLLMConfig] = {}

    # ------------------------------------------------------------------
    def refresh_if_needed(self, force: bool = False) -> None:
        with self._lock:
            if force or self._requires_refresh():
                asyncio.run(self._load_async())

    def _requires_refresh(self) -> bool:
        signature = asyncio.run(self._fetch_signature())
        if signature != self._signature:
            self._signature = signature
            return True
        return False

    async def _fetch_signature(self) -> tuple:
        async for session in self._db_manager.get_session():
            agent_stmt = select(func.max(AgentConfig.updated_at), func.count(AgentConfig.id))
            llm_stmt = select(func.max(AgentLLMConfig.updated_at), func.count(AgentLLMConfig.id))

            agent_max, agent_count = (await session.execute(agent_stmt)).one()
            llm_max, llm_count = (await session.execute(llm_stmt)).one()

            return (
                agent_max.isoformat() if isinstance(agent_max, datetime) else None,
                int(agent_count or 0),
                llm_max.isoformat() if isinstance(llm_max, datetime) else None,
                int(llm_count or 0),
            )
        return (None, 0, None, 0)

    async def _load_async(self) -> None:
        async for session in self._db_manager.get_session():
            agents = (await session.execute(select(AgentConfig))).scalars().all()

            llm_rows = (
                await session.execute(
                    select(AgentLLMConfig).where(AgentLLMConfig.enabled == True)  # noqa: E712
                )
            ).scalars().all()

            llm_mapping: Dict[int, AgentLLMConfig] = {}
            for cfg in sorted(llm_rows, key=lambda c: c.updated_at, reverse=True):
                if cfg.agent_id not in llm_mapping:
                    llm_mapping[cfg.agent_id] = cfg

            self._agents = {agent.name: agent for agent in agents}
            self._llm_configs = llm_mapping
            break

    # ------------------------------------------------------------------
    def get_llm(self, agent_name: str, default_type: str) -> Optional[ManagedLLM]:
        self.refresh_if_needed()
        with self._lock:
            agent = self._agents.get(agent_name)
            config = self._llm_configs.get(agent.id) if agent else None
        return self._build_managed_llm(agent_name, agent, config, default_type)

    def agent_has_config(self, agent_name: str) -> bool:
        self.refresh_if_needed()
        with self._lock:
            agent = self._agents.get(agent_name)
            if not agent:
                return False
            return agent.id in self._llm_configs

    def provider_status(self) -> Dict[str, Any]:
        self.refresh_if_needed()
        status: Dict[str, Any] = {}
        with self._lock:
            for name, agent in self._agents.items():
                cfg = self._llm_configs.get(agent.id)
                provider = (cfg.provider if cfg else agent.llm_provider or self._base_config.get("llm_provider", "openai")).lower()
                model = cfg.model_name if cfg else agent.llm_model or self._base_config.get("quick_think_llm")
                entry = status.setdefault(provider, {"agents": [], "models": set()})
                entry["agents"].append(name)
                if model:
                    entry["models"].add(model)
        for payload in status.values():
            payload["models"] = sorted(payload["models"])
        return status

    # ------------------------------------------------------------------
    def _resolve_api_key(self, provider: str, encrypted: Optional[str]) -> Optional[str]:
        if encrypted:
            try:
                return decrypt_api_key(encrypted)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to decrypt API key for provider %s: %s", provider, exc)
                return None
        env_key = _API_KEY_ENV_ALIASES.get(provider.lower(), f"{provider.upper()}_API_KEY")
        return os.getenv(env_key)

    def _model_cost_info(self, provider: str, model_name: str) -> tuple[float, float]:
        try:
            provider_enum = ProviderType(provider.lower())
            info = get_model_info(provider_enum, model_name)
            return info.cost_per_1k_input_tokens, info.cost_per_1k_output_tokens
        except Exception:
            logger.debug("Unknown cost profile for provider=%s model=%s", provider, model_name)
            return 0.0, 0.0

    def _build_info(
        self,
        provider: str,
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
        top_p: Optional[float],
        metadata: Optional[Dict[str, Any]],
    ) -> _LLMClientInfo:
        input_cost, output_cost = self._model_cost_info(provider, model_name)
        return _LLMClientInfo(
            provider=provider,
            model_name=model_name,
            cost_per_1k_input_tokens=input_cost,
            cost_per_1k_output_tokens=output_cost,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            metadata=metadata or {},
        )

    def _create_llm_instance(
        self,
        *,
        provider: str,
        model_name: str,
        api_key: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        top_p: Optional[float],
        metadata: Optional[Dict[str, Any]],
    ) -> Optional[RunnableSerializable]:
        if not api_key:
            logger.warning("Missing API key for provider '%s'", provider)
            return None
        kwargs = metadata.copy() if metadata else {}
        try:
            provider_instance = ProviderFactory.create_provider(
                provider_type=provider,
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs,
            )
            return provider_instance.client
        except Exception as exc:
            logger.error("Failed to initialise provider %s/%s: %s", provider, model_name, exc)
            return None

    def _build_managed_llm(
        self,
        agent_name: str,
        agent: Optional[AgentConfig],
        config: Optional[AgentLLMConfig],
        default_type: str,
    ) -> Optional[ManagedLLM]:
        llm_type = (config.llm_type if hasattr(config, "llm_type") else None) or (agent.llm_type if agent else default_type)

        provider = (config.provider if config else agent.llm_provider if agent else self._base_config.get("llm_provider", "openai")).lower()
        model_name = (
            config.model_name if config else agent.llm_model if agent and agent.llm_model else (
                self._base_config.get("quick_think_llm") if llm_type == "quick" else self._base_config.get("deep_think_llm")
            )
        )
        if not model_name:
            logger.error("No model configured for agent '%s'", agent_name)
            return None

        metadata: Dict[str, Any] = {}
        if config and config.metadata_json:
            try:
                metadata = json.loads(config.metadata_json)
            except json.JSONDecodeError:
                metadata = {}

        temperature = config.temperature if config else agent.temperature if agent else self._base_config.get("temperature", 0.7)
        max_tokens = config.max_tokens if config else agent.max_tokens if agent else self._base_config.get("max_tokens")
        top_p = config.top_p if config else None

        api_key = self._resolve_api_key(provider, config.api_key_encrypted if config else None)
        primary_model = self._create_llm_instance(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            metadata=metadata,
        )
        if primary_model is None:
            return None

        primary_info = self._build_info(provider, model_name, temperature, max_tokens, top_p, metadata)

        fallback_model = None
        fallback_info = None
        if config and config.fallback_provider and config.fallback_model:
            fb_provider = config.fallback_provider.lower()
            fb_metadata = metadata.get("fallback", {}) if metadata else {}
            fb_key = self._resolve_api_key(fb_provider, None)
            fallback_model = self._create_llm_instance(
                provider=fb_provider,
                model_name=config.fallback_model,
                api_key=fb_key,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                metadata=fb_metadata,
            )
            if fallback_model:
                fallback_info = self._build_info(
                    fb_provider,
                    config.fallback_model,
                    temperature,
                    max_tokens,
                    top_p,
                    fb_metadata,
                )

        agent_id = agent.id if agent else 0
        return ManagedLLM(
            agent_id=agent_id,
            agent_name=agent_name,
            primary=primary_model,
            primary_info=primary_info,
            usage_recorder=self._usage_recorder,
            fallback=fallback_model,
            fallback_info=fallback_info,
        )
