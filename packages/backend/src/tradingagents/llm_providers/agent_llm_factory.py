from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from sqlmodel import select

from app.db import AgentConfig, AgentLLMConfig, DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-4"
DEFAULT_TEMPERATURE = 0.7

API_KEY_ENV_MAP = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "grok": "GROK_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}

BASE_URL_ENV_MAP = {
    "deepseek": "DEEPSEEK_BASE_URL",
    "grok": "GROK_BASE_URL",
}

DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "grok": "https://api.x.ai/v1",
}

DEFAULT_API_KEY_FALLBACKS = {
    "openai": "test-api-key",
    "deepseek": "test-api-key",
    "grok": "test-api-key",
    "anthropic": "test-api-key",
    "claude": "test-api-key",
    "google": "test-api-key",
}

_LLM_CACHE: dict[str, Any] = {}


def clear_llm_cache() -> None:
    """Clear the cached LLM instances."""

    _LLM_CACHE.clear()


def get_llm_for_agent(agent_id: int, db_manager: Optional[DatabaseManager] = None) -> Any:
    """Return an LLM configured for the given agent ID.

    Args:
        agent_id: Identifier of the agent whose LLM should be returned.
        db_manager: Optional database manager. Falls back to the global manager if not provided.

    Returns:
        A configured LangChain chat model instance. Falls back to a default OpenAI model when
        no configuration is found or the database is unavailable.
    """

    cache_key = _cache_key_for_agent(agent_id)
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key]

    manager = _resolve_db_manager(db_manager)
    llm_instance: Any | None = None

    if manager is not None:
        try:
            config = _run_db_coro(_query_agent_llm_config(agent_id, manager))
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to load LLM config for agent %s: %s", agent_id, exc)
            config = None

        if config and config.enabled:
            llm_instance = _create_llm_from_config(config)
        else:
            if config and not config.enabled:
                logger.info(
                    "Agent %s LLM config is disabled; using default configuration", agent_id
                )
    else:
        logger.debug("Database manager unavailable; using default LLM for agent %s", agent_id)

    if llm_instance is None:
        llm_instance = _create_default_llm()

    _LLM_CACHE[cache_key] = llm_instance
    return llm_instance


def get_llm_for_agent_by_name(
    agent_name: str, db_manager: Optional[DatabaseManager] = None
) -> Any:
    """Return an LLM configured for the agent identified by name.

    Args:
        agent_name: The agent's unique name.
        db_manager: Optional database manager override.

    Returns:
        A configured LangChain chat model instance.
    """

    cache_key = _cache_key_for_name(agent_name)
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key]

    manager = _resolve_db_manager(db_manager)
    if manager is None:
        llm = _create_default_llm()
        _LLM_CACHE[cache_key] = llm
        return llm

    try:
        agent = _run_db_coro(_query_agent_by_name(agent_name, manager))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to load agent %s: %s", agent_name, exc)
        agent = None

    if agent is None:
        llm = _create_default_llm()
        _LLM_CACHE[cache_key] = llm
        return llm

    llm = get_llm_for_agent(agent.id, manager)
    _LLM_CACHE[cache_key] = llm
    return llm


def _cache_key_for_agent(agent_id: int) -> str:
    return f"id:{agent_id}"


def _cache_key_for_name(agent_name: str) -> str:
    return f"name:{agent_name.lower()}"


def _resolve_db_manager(db_manager: Optional[DatabaseManager]) -> Optional[DatabaseManager]:
    if db_manager is not None:
        return db_manager
    try:
        return get_db_manager()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Global database manager unavailable: %s", exc)
        return None


async def _query_agent_llm_config(
    agent_id: int, db_manager: DatabaseManager
) -> Optional[AgentLLMConfig]:
    """Fetch the enabled LLM configuration for an agent."""

    async for session in db_manager.get_session():
        stmt = (
            select(AgentLLMConfig)
            .where(AgentLLMConfig.agent_id == agent_id)
            .where(AgentLLMConfig.enabled == True)  # noqa: E712
            .order_by(AgentLLMConfig.updated_at.desc())
            .limit(1)
        )
        result = await session.exec(stmt)
        return result.first()
    return None


async def _query_agent_by_name(
    agent_name: str, db_manager: DatabaseManager
) -> Optional[AgentConfig]:
    """Fetch an agent row by its unique name."""

    async for session in db_manager.get_session():
        stmt = select(AgentConfig).where(AgentConfig.name == agent_name)
        result = await session.exec(stmt)
        return result.first()
    return None


def _run_db_coro(coro: "asyncio.Future[Any]") -> Any:
    """Execute an async database coroutine in both sync and async contexts."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_container: list[Any] = []
    error_container: list[BaseException] = []

    def _runner() -> None:
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            result = new_loop.run_until_complete(coro)
            result_container.append(result)
        except BaseException as exc:  # pragma: no cover - defensive logging
            error_container.append(exc)
        finally:
            try:
                new_loop.run_until_complete(new_loop.shutdown_asyncgens())
            except Exception:  # pragma: no cover
                pass
            finally:
                asyncio.set_event_loop(None)
                new_loop.close()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if error_container:
        raise error_container[0]

    return result_container[0] if result_container else None


def _create_llm_from_config(config: AgentLLMConfig) -> Any:
    provider = (config.provider or DEFAULT_PROVIDER).lower()
    api_key = _resolve_api_key(provider, config)
    model_name = config.model_name or DEFAULT_MODEL
    temperature = config.temperature or DEFAULT_TEMPERATURE
    max_tokens = config.max_tokens
    top_p = config.top_p

    try:
        return _instantiate_llm(provider, model_name, temperature, max_tokens, top_p, api_key)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Failed to instantiate LLM for agent %s with provider %s: %s",
            config.agent_id,
            provider,
            exc,
        )
        return _create_default_llm()


def _create_default_llm() -> Any:
    api_key = _resolve_api_key(DEFAULT_PROVIDER)
    return _instantiate_llm(DEFAULT_PROVIDER, DEFAULT_MODEL, DEFAULT_TEMPERATURE, None, None, api_key)


def _resolve_api_key(provider: str, config: Optional[AgentLLMConfig] = None) -> Optional[str]:
    if config and getattr(config, "api_key_encrypted", None):
        try:
            from app.security.encryption import decrypt_api_key

            decrypted = decrypt_api_key(config.api_key_encrypted)
            if decrypted:
                return decrypted
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to decrypt API key for agent %s: %s",
                getattr(config, "agent_id", "unknown"),
                exc,
            )

    env_var = API_KEY_ENV_MAP.get(provider.lower())
    if env_var:
        value = os.getenv(env_var)
        if value:
            return value

    fallback = DEFAULT_API_KEY_FALLBACKS.get(provider.lower())
    if fallback:
        logger.debug(
            "Using placeholder API key for provider %s; configure a real key in production",
            provider,
        )
        return fallback
    return None


def _instantiate_llm(
    provider: str,
    model_name: str,
    temperature: float,
    max_tokens: Optional[int],
    top_p: Optional[float],
    api_key: Optional[str],
) -> Any:
    provider = provider.lower()

    if provider in {"openai", "deepseek", "grok"}:
        kwargs: dict[str, Any] = {"model": model_name, "temperature": temperature}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if top_p is not None:
            kwargs["top_p"] = top_p
        if api_key:
            kwargs["api_key"] = api_key

        if provider in {"deepseek", "grok"}:
            base_url_env = BASE_URL_ENV_MAP.get(provider)
            base_url = (
                os.getenv(base_url_env) if base_url_env else None
            ) or DEFAULT_BASE_URLS.get(provider)
            if base_url:
                kwargs["base_url"] = base_url

        return ChatOpenAI(**kwargs)

    if provider in {"anthropic", "claude"}:
        kwargs = {"model": model_name, "temperature": temperature}
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if api_key:
            kwargs["api_key"] = api_key
        return ChatAnthropic(**kwargs)

    if provider == "google":
        kwargs = {"model": model_name, "temperature": temperature}
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if top_p is not None:
            kwargs["top_p"] = top_p
        if api_key:
            kwargs["api_key"] = api_key
        return ChatGoogleGenerativeAI(**kwargs)

    logger.warning("Unsupported provider '%s'; falling back to OpenAI", provider)
    return _instantiate_llm("openai", model_name, temperature, max_tokens, top_p, api_key)
