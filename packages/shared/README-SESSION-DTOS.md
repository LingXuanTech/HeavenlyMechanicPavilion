# Session DTOs - Implementation Guide

## Overview

The shared package now includes comprehensive DTOs for persisted session contracts, allowing frontend and backend to maintain type-safe communication for session summaries and event history.

## New Types

### SessionSummary

Lightweight summary of a persisted session without full event history:

```typescript
interface SessionSummary {
  id: string;
  ticker: string;
  asOfDate: string;
  status: "pending" | "running" | "completed" | "failed";
  createdAt: string;
  updatedAt?: string;
}
```

Maps to backend's session metadata. Use this for session lists and lightweight displays.

### SessionEventSummary

A single buffered event with timestamp (maps to backend's `BufferedSessionEvent`):

```typescript
interface SessionEventSummary {
  timestamp: string;
  event: Record<string, unknown>;
}
```

### SessionEventsHistory

Complete event history response (maps to backend's `SessionEventsHistoryResponse`):

```typescript
interface SessionEventsHistory {
  session_id: string;
  events: SessionEventSummary[];
  count: number;
}
```

## Usage Examples

### 1. Type Guards

Validate backend responses safely:

```typescript
import { isSessionSummary, isSessionEventsHistory } from '@tradingagents/shared/domain';

const response = await fetch('/api/sessions/123');
const data = await response.json();

if (isSessionSummary(data)) {
  // TypeScript now knows data is SessionSummary
  console.log(data.ticker, data.status);
} else {
  console.error('Invalid session summary');
}
```

### 2. Normalizers

Transform raw backend JSON into typed structures:

```typescript
import { normalizeSessionSummary, normalizeSessionEventsHistory } from '@tradingagents/shared/domain';

// Returns SessionSummary | null
const summary = normalizeSessionSummary(rawBackendResponse);
if (!summary) {
  throw new Error('Malformed session data');
}

// Returns SessionEventsHistory | null
const history = normalizeSessionEventsHistory(rawEventsResponse);
if (!history) {
  throw new Error('Malformed events data');
}
```

### 3. Enrichment Helper

Transform lightweight summaries into full `TradingSession` objects:

```typescript
import { enrichSessionWithEvents } from '@tradingagents/shared/domain';

// Fetch session summary
const summaryResponse = await fetch('/api/sessions/123/summary');
const summary = normalizeSessionSummary(await summaryResponse.json());

// Optionally fetch event history
const historyResponse = await fetch('/api/sessions/123/events-history');
const eventsHistory = normalizeSessionEventsHistory(await historyResponse.json());

// Merge into rich TradingSession object
const tradingSession = enrichSessionWithEvents(summary, eventsHistory);

// Now you have a full TradingSession with agents, insights, decision, and risk
console.log(tradingSession.agents.length);
console.log(tradingSession.decision?.action);
```

## Backend Alignment

These DTOs map directly to backend schemas:

| Frontend Type | Backend Schema |
|--------------|----------------|
| `SessionSummary` | Session metadata (id, ticker, status, dates) |
| `SessionEventSummary` | `BufferedSessionEvent` from `app/schemas/sessions.py` |
| `SessionEventsHistory` | `SessionEventsHistoryResponse` from `app/schemas/sessions.py` |

## Event Payload Extraction

The `enrichSessionWithEvents` helper extracts structured data from event payloads:

- **agent_update** events → `AgentSnapshot[]`
- **insight** events → `TradingInsight[]`
- **decision** events → `TradingSession.decision`
- **risk** events → `TradingSession.risk`

Malformed event payloads are safely ignored rather than throwing errors.

## Testing

All DTOs have comprehensive test coverage (37 tests):

- Type guard validation (valid and invalid inputs)
- Normalizer functions (success and failure cases)
- Enrichment helper (various scenarios and edge cases)
- Handling of malformed payloads

Run tests:

```bash
cd packages/shared
pnpm test
```

## Example: Fetching Session History

```typescript
import {
  normalizeSessionSummary,
  normalizeSessionEventsHistory,
  enrichSessionWithEvents,
  type TradingSession,
} from '@tradingagents/shared/domain';

async function fetchSessionDetails(sessionId: string): Promise<TradingSession | null> {
  try {
    // Fetch session summary
    const summaryResponse = await fetch(`/api/sessions/${sessionId}`);
    const summaryData = await summaryResponse.json();
    const summary = normalizeSessionSummary(summaryData);
    
    if (!summary) {
      console.error('Invalid session summary');
      return null;
    }

    // Fetch event history (optional)
    let eventsHistory = null;
    try {
      const historyResponse = await fetch(`/api/sessions/${sessionId}/events-history`);
      const historyData = await historyResponse.json();
      eventsHistory = normalizeSessionEventsHistory(historyData);
    } catch (err) {
      console.warn('Could not fetch event history:', err);
    }

    // Enrich summary with events
    return enrichSessionWithEvents(summary, eventsHistory ?? undefined);
  } catch (err) {
    console.error('Failed to fetch session:', err);
    return null;
  }
}

// Usage
const session = await fetchSessionDetails('session-123');
if (session) {
  console.log(`${session.ticker} - ${session.status}`);
  console.log(`Agents: ${session.agents.length}`);
  console.log(`Insights: ${session.insights.length}`);
  if (session.decision) {
    console.log(`Decision: ${session.decision.action} (${session.decision.conviction})`);
  }
}
```

## No Circular Dependencies

All types are defined in the shared package and can be imported by both frontend and backend without circular dependencies:

```typescript
// Frontend
import { SessionSummary, enrichSessionWithEvents } from '@tradingagents/shared/domain';

// Backend can also use for TypeScript tooling (if needed)
import type { SessionSummary } from '@tradingagents/shared/domain';
```

## Changes Made

1. **Extended `src/domain/session.ts`** with:
   - New interfaces: `SessionSummary`, `SessionEventSummary`, `SessionEventsHistory`
   - Type guards: `isSessionSummary`, `isSessionEventSummary`, `isSessionEventsHistory`
   - Normalizers: `normalizeSessionSummary`, `normalizeSessionEventsHistory`
   - Helper: `enrichSessionWithEvents`
   - Internal type guards for event payload validation

2. **Created `tests/domain/session.test.ts`** with 37 comprehensive tests

3. **Updated `package.json`** to include `@types/node` dependency

4. **Fixed `tsconfig.json`** to use `moduleResolution: "Bundler"` for compatibility

All existing exports remain unchanged, ensuring backward compatibility.
