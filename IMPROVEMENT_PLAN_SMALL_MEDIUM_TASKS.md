# Focused Project Analysis & Improvement Plan (Small/Medium Tasks)

## Current Architecture Snapshot

- **Monorepo structure**: PNPM workspace with a Python FastAPI backend (`packages/backend`), a Next.js 14 control center (`packages/frontend`), and shared TypeScript utilities (`packages/shared`).
- **Agent workflow orchestration**: `TradingGraphService` (`packages/backend/app/services/graph.py`) wraps the LangGraph workflow, exposing async session execution and SSE/WebSocket streaming through `SessionEventManager`.
- **Streaming interfaces**: `/sessions/{id}/events` SSE (`packages/backend/app/api/streams.py`) and Redis-backed real-time channels (`packages/backend/app/api/streaming.py`) feed the frontend Zustand real-time store (`packages/frontend/src/lib/store/use-realtime-store.ts`).
- **Provider ecosystem**: LLM provider APIs exist under `src/llm_providers`, while the FastAPI surface imports from `tradingagents.llm_providers`, leaving the intended factory/registry layer partially stubbed.

## Key Observations

### Strengths
- Clear separation between orchestration (`TradingGraphService`) and transport (`SessionEventManager`, SSE/WS routes).
- Robust security middleware stack (Auth, rate limiting, compression, error handling) already wired in `app/main.py`.
- Frontend real-time store prepared for multiple data feeds, with shared clients for SSE/WebSocket connections.

### Risks & Gaps
- **Duplicated LLM provider namespaces**: `tradingagents.llm_providers` advertises a factory/registry that is commented out while live implementations live in `src/llm_providers`; `/api/llm-providers` currently imports symbols that are not exported (see `packages/backend/app/api/llm_providers.py` vs `packages/backend/src/tradingagents/llm_providers/__init__.py`).
- **Hard-coded provider catalog**: `AgentLLMService` maintains a static `SUPPORTED_PROVIDERS` map (`packages/backend/app/services/agent_llm_service.py`), drifting from the real provider registry and blocking dynamic providers.
- **Session persistence gap**: Backend exposes `POST /sessions` only; the frontend expects `/api/sessions` & `/api/sessions/{id}` responses with historical data (`packages/frontend/src/components/sessions/session-manager.tsx`, `.../sessions/[sessionId]/page.tsx`).
- **Simulated broker realism**: `SimulatedBroker.get_market_price` returns random prices (TODO at lines 393-404) instead of querying vendor plugins, making execution paths non-deterministic and untestable.
- **Agent hot-reload TODO**: `_trigger_hot_reload` in `AgentConfigService` leaves custom agent loading unimplemented (lines 233-245).
- **Frontend API client drift**: The Next.js client reimplements HTTP helpers with `any` responses (`packages/frontend/src/lib/api/client.ts`) instead of using the typed shared clients, weakening type safety and error handling.
- **Realtime UX gaps**: Session detail pages don't surface live SSE updates yet, despite the store wiring being in place.

## Improvement Plan (Small/Medium Tasks)

| ID | Area | Task | Description | Impact | Size |
| --- | --- | --- | --- | --- | --- |
| B-1 | Backend · LLM | Restore `ProviderFactory` & registry exports under `tradingagents.llm_providers` | Move/rehydrate the factory and registry modules currently living in `src/llm_providers` so `app/api/llm_providers.py` can import `ProviderFactory` & `list_providers` without commented stubs. Includes updating tests to cover the canonical namespace. | Enables provider endpoints, unblocks runtime imports, reduces duplication. | Medium |
| B-2 | Backend · LLM | Replace static provider list in `AgentLLMService` | Wire `AgentLLMService` to consume the normalized provider registry (task B-1) instead of the hard-coded `SUPPORTED_PROVIDERS` dict, adding graceful error handling when providers/models are disabled. | Keeps API + DB aligned with actual provider capabilities. | Medium |
| B-3 | Backend · LLM | Add validation tests for `/api/llm-providers/validate-key` | Introduce FastAPI test cases using dependency overrides to mock provider health checks, verifying success/failure payloads and error propagation. | Prevents regressions once tasks B-1/B-2 ship. | Small |
| B-4 | Backend · Execution | Introduce `MarketDataService` and swap `SimulatedBroker` price lookup | Create an injectable service that queries the vendor plugin registry for quotes (with deterministic fallback) and update `SimulatedBroker.get_market_price` to use it instead of random values. Add unit tests for both success/fallback paths. | Makes trades reproducible, unlocks integration with real vendor data. | Medium |
| B-5 | Backend · Sessions | Persist session metadata & expose REST listing | Add a `trading_sessions` table + SQLModel, record metadata when `run_session` is called, and implement `GET /sessions` & `GET /sessions/{id}` endpoints returning the payload shape expected by the frontend. | Aligns backend with UI expectations and enables history. | Medium |
| B-6 | Backend · Sessions | Capture recent session events for REST consumers | Extend `SessionEventManager` to retain a timestamped ring buffer per session so the new REST endpoints (B-5) can return latest status snippets without scraping Redis/SSE. | Provides context for dashboards without active streams. | Small |
| B-7 | Backend · Agents | Load custom agent plugins from DB on hot-reload | Complete the TODO in `_trigger_hot_reload` to hydrate user-defined agent plugins from persisted configs before re-registering built-ins. Add integration coverage to assert registry contents after create/update. | Enables runtime customization promised by API. | Medium |
| F-1 | Frontend · UX | Add loading skeletons & error toasts to `SessionManager` | Replace the "Loading sessions..." string with skeleton cards, surface API errors via toast/non-blocking banner, and guard against missing data until B-5 lands. | Improves perceived performance and resilience. | Small |
| F-2 | Frontend · API | Migrate API client to shared typed HttpClient | Replace `fetchAPI` in `frontend/src/lib/api/client.ts` with the shared `HttpClient`, returning typed domain models (`@tradingagents/shared/domain`). Update session components to use the typed responses. | Reduces drift between frontend/backend contracts. | Medium |
| F-3 | Frontend · Realtime | Render live agent activity on session detail | Wrap `useRealtimeStore` SSE hook into the session detail page to stream `/sessions/{id}/events`, display activity timeline, and ensure cleanup on unmount. | Delivers the real-time experience the backend already emits. | Medium |
| S-1 | Shared · Types | Publish session DTO helpers & tests | Extend `packages/shared/src/domain/session.ts` with helpers/type guards for persisted session + event summaries, and add Vitest coverage so both backend serializers and frontend consumers share the same shape. | Keeps shared contract versioned and test-covered. | Small |
| DX-1 | DevEx | Add integration tests for session lifecycle | Create pytest scenarios covering `POST /sessions`, SSE event emission, and the new REST retrieval (B-5/B-6) using an in-memory SQLite database. | Locks in end-to-end behavior for future refactors. | Medium |
| DOC-1 | Docs | Update architecture & API docs for session persistence & provider flow | Document the unified provider architecture and the new session endpoints/market data service in `docs/ARCHITECTURE.md` & `docs/API.md`, plus add troubleshooting tips for missing Redis/vendor credentials. | Keeps contributors aligned with the updated system. | Medium |

### Task Size Legend
- **Small**: ≤ 0.5 engineering day, low risk, typically scoped to one module/test suite.
- **Medium**: 0.5–2 engineering days, may cross layers but still tractable without dedicated spike.

## Suggested Sequencing & Dependencies
1. **Stabilize LLM infrastructure**: Complete B-1 → B-2 → B-3 to ensure provider APIs are reliable before layering additional features that rely on them.
2. **Session persistence loop**: Implement B-5 alongside B-6, then cover with DX-1 tests and document via DOC-1. Frontend task F-1 can ship earlier to harden UX; F-2/F-3 should follow once the backend contracts (B-5/B-6/S-1) are ready.
3. **Execution realism**: Deliver B-4 after the provider registry work so vendor integrations are ready. This also benefits from S-1 to standardize payloads if quotes are surfaced in the UI later.
4. **Agent customization**: Finish B-7 after provider registry unification to ensure plugin loading can reuse the same discovery mechanisms.

By executing the above small and medium-scoped tasks, the team can incrementally close the most critical functional gaps (provider registry, session persistence, deterministic execution paths) while delivering immediate UX and documentation improvements that keep the monorepo cohesive.
