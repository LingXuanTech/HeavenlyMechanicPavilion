"""Feature completeness checks for TradingAgents core functionality.

This module provides a lightweight validation layer that inspects key features
shipped as part of the recent roadmap work. The checks avoid heavy runtime
dependencies and instead focus on verifying that critical modules, methods, and
schemas are present and wired together as expected. The output is consumed by
an API endpoint that surfaces a human-friendly checklist.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

CheckResult = Tuple[bool, Optional[str]]


@dataclass(slots=True)
class FeatureCheckDefinition:
    """Definition of a feature completeness check."""

    name: str
    description: str
    check: Callable[[], CheckResult]


@dataclass(slots=True)
class FeatureCheckResult:
    """Outcome of a feature completeness check."""

    name: str
    description: str
    passed: bool
    detail: Optional[str] = None


@dataclass(slots=True)
class FeatureCheckSummary:
    """Aggregate summary for a collection of feature checks."""

    status: str
    passed: int
    failed: int
    total: int


def _check_session_event_buffer() -> CheckResult:
    """Ensure session event buffering is available for REST consumers."""

    from app.services.events import SessionEventManager

    manager = SessionEventManager()

    if not hasattr(manager, "_event_buffers"):
        return False, "SessionEventManager missing _event_buffers storage"
    if not hasattr(manager, "get_recent_events"):
        return False, "SessionEventManager missing get_recent_events helper"

    events = manager.get_recent_events("nonexistent-session")
    if events != []:
        return False, "Expected empty list for sessions without buffered events"

    return True, None


def _check_analysis_session_persistence() -> CheckResult:
    """Verify analysis sessions are persisted with the expected API surface."""

    from app.db.models.analysis_session import AnalysisSession
    from app.services.analysis_session import AnalysisSessionService

    required_fields = (
        "id",
        "ticker",
        "status",
        "trade_date",
        "created_at",
        "updated_at",
    )
    missing_fields = [field for field in required_fields if not hasattr(AnalysisSession, field)]
    if missing_fields:
        return False, f"AnalysisSession missing fields: {', '.join(missing_fields)}"

    required_methods = (
        "create_session",
        "update_status",
        "get_session",
        "list_sessions",
        "get_session_events",
    )
    missing_methods = [method for method in required_methods if not hasattr(AnalysisSessionService, method)]
    if missing_methods:
        return False, f"AnalysisSessionService missing methods: {', '.join(missing_methods)}"

    return True, None


def _check_llm_provider_registry() -> CheckResult:
    """Confirm the canonical LLM provider registry exposes expected metadata."""

    from tradingagents.llm_providers import ProviderType, get_provider_info, list_models

    try:
        info = get_provider_info(ProviderType.OPENAI)
    except Exception as exc:  # pragma: no cover - defensive guard
        return False, f"Failed to access provider registry: {exc}"

    if not info or not info.models:
        return False, "OpenAI provider metadata is not populated"

    models = list_models("openai")
    if not models:
        return False, "list_models returned no results for openai"

    return True, None


def _check_agent_llm_service_registry_integration() -> CheckResult:
    """Ensure AgentLLMService defers to the canonical provider registry."""

    from app.services.agent_llm_service import AgentLLMService

    required_methods = (
        "_coerce_provider_type",
        "_validate_provider_and_model",
        "_get_cost_defaults",
        "validate_config",
    )
    missing_methods = [method for method in required_methods if not hasattr(AgentLLMService, method)]
    if missing_methods:
        return False, f"AgentLLMService missing methods: {', '.join(missing_methods)}"

    if not inspect.iscoroutinefunction(AgentLLMService.validate_config):
        return False, "AgentLLMService.validate_config must be asynchronous"

    return True, None


def _check_market_data_service() -> CheckResult:
    """Ensure deterministic market data fallbacks are available for simulation."""

    from app.services.market_data import MarketDataService

    if not inspect.iscoroutinefunction(MarketDataService.get_latest_price):
        return False, "MarketDataService.get_latest_price must be asynchronous"

    service = MarketDataService(fallback_prices={"TA_TEST": 123.45})
    fallback_price = service._build_fallback_price("TA_TEST")  # type: ignore[attr-defined]

    if getattr(fallback_price, "last", None) != 123.45:
        return False, "Fallback market price did not preserve configured baseline"

    return True, None


def _check_agent_hot_reload() -> CheckResult:
    """Verify custom agent hot-reload leverages the database-backed registry."""

    from app.services.agent_config import AgentConfigService

    if not hasattr(AgentConfigService, "_trigger_hot_reload"):
        return False, "AgentConfigService missing _trigger_hot_reload"

    if not inspect.iscoroutinefunction(AgentConfigService._trigger_hot_reload):
        return False, "AgentConfigService._trigger_hot_reload must be asynchronous"

    return True, None


def _check_session_events_history_endpoint() -> CheckResult:
    """Ensure session event history is exposed over REST."""

    from app.api.streams import session_recent_events
    from app.schemas.sessions import SessionEventsHistoryResponse

    if not inspect.iscoroutinefunction(session_recent_events):
        return False, "session_recent_events endpoint must be asynchronous"

    signature = inspect.signature(session_recent_events)
    if "session_id" not in signature.parameters:
        return False, "session_recent_events missing session_id parameter"

    if "events" not in SessionEventsHistoryResponse.model_fields:
        return False, "SessionEventsHistoryResponse missing events field"

    return True, None


FEATURE_CHECKS: List[FeatureCheckDefinition] = [
    FeatureCheckDefinition(
        name="session-event-buffer",
        description="SessionEventManager retains recent events with timestamps for REST clients.",
        check=_check_session_event_buffer,
    ),
    FeatureCheckDefinition(
        name="analysis-session-persistence",
        description="Analysis sessions persist metadata and expose listing/detail services.",
        check=_check_analysis_session_persistence,
    ),
    FeatureCheckDefinition(
        name="llm-provider-registry",
        description="LLM provider registry exposes canonical metadata and model listings.",
        check=_check_llm_provider_registry,
    ),
    FeatureCheckDefinition(
        name="agent-llm-registry-integration",
        description="AgentLLMService relies on the provider registry for validation and costs.",
        check=_check_agent_llm_service_registry_integration,
    ),
    FeatureCheckDefinition(
        name="market-data-service",
        description="MarketDataService offers deterministic fallback pricing for simulations.",
        check=_check_market_data_service,
    ),
    FeatureCheckDefinition(
        name="agent-hot-reload",
        description="AgentConfigService hot-reloads custom agents from the database asynchronously.",
        check=_check_agent_hot_reload,
    ),
    FeatureCheckDefinition(
        name="session-events-history-endpoint",
        description="REST endpoint exposes buffered session events aligned with shared DTOs.",
        check=_check_session_events_history_endpoint,
    ),
]


def run_feature_checks() -> List[FeatureCheckResult]:
    """Execute all registered feature checks and return their results."""

    results: List[FeatureCheckResult] = []
    for definition in FEATURE_CHECKS:
        try:
            passed, detail = definition.check()
        except Exception as exc:  # pragma: no cover - defensive guard
            passed = False
            detail = f"{type(exc).__name__}: {exc}"

        results.append(
            FeatureCheckResult(
                name=definition.name,
                description=definition.description,
                passed=passed,
                detail=detail,
            )
        )

    return results


def summarize_feature_checks(results: List[FeatureCheckResult]) -> FeatureCheckSummary:
    """Produce a high-level summary for feature check results."""

    total = len(results)
    passed = sum(1 for result in results if result.passed)
    failed = total - passed
    status = "complete" if failed == 0 else "incomplete"

    return FeatureCheckSummary(status=status, passed=passed, failed=failed, total=total)


__all__ = [
    "FeatureCheckDefinition",
    "FeatureCheckResult",
    "FeatureCheckSummary",
    "FEATURE_CHECKS",
    "run_feature_checks",
    "summarize_feature_checks",
]
