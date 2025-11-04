import { describe, it, expect } from 'vitest'

import {
  isSessionSummary,
  isSessionEventSummary,
  isSessionEventsHistory,
  normalizeSessionSummary,
  normalizeSessionEventsHistory,
  enrichSessionWithEvents,
  type SessionSummary,
  type SessionEventSummary,
  type SessionEventsHistory,
  type TradingSession,
} from '../../src/domain/session'

describe('SessionSummary type guard', () => {
  it('accepts valid SessionSummary', () => {
    const valid: SessionSummary = {
      id: 'session-123',
      ticker: 'AAPL',
      asOfDate: '2024-03-15',
      status: 'completed',
      createdAt: '2024-03-15T10:00:00Z',
      updatedAt: '2024-03-15T11:00:00Z',
    }

    expect(isSessionSummary(valid)).toBe(true)
  })

  it('accepts SessionSummary without optional updatedAt', () => {
    const valid = {
      id: 'session-456',
      ticker: 'TSLA',
      asOfDate: '2024-03-16',
      status: 'running',
      createdAt: '2024-03-16T09:00:00Z',
    }

    expect(isSessionSummary(valid)).toBe(true)
  })

  it('rejects null', () => {
    expect(isSessionSummary(null)).toBe(false)
  })

  it('rejects undefined', () => {
    expect(isSessionSummary(undefined)).toBe(false)
  })

  it('rejects object with missing required fields', () => {
    const invalid = {
      id: 'session-789',
      ticker: 'MSFT',
      // missing asOfDate, status, createdAt
    }

    expect(isSessionSummary(invalid)).toBe(false)
  })

  it('rejects object with invalid status', () => {
    const invalid = {
      id: 'session-999',
      ticker: 'GOOGL',
      asOfDate: '2024-03-17',
      status: 'invalid-status',
      createdAt: '2024-03-17T08:00:00Z',
    }

    expect(isSessionSummary(invalid)).toBe(false)
  })

  it('rejects object with wrong types', () => {
    const invalid = {
      id: 123, // should be string
      ticker: 'NFLX',
      asOfDate: '2024-03-18',
      status: 'pending',
      createdAt: '2024-03-18T07:00:00Z',
    }

    expect(isSessionSummary(invalid)).toBe(false)
  })
})

describe('SessionEventSummary type guard', () => {
  it('accepts valid SessionEventSummary', () => {
    const valid: SessionEventSummary = {
      timestamp: '2024-03-15T10:30:00Z',
      event: {
        type: 'agent_update',
        payload: { agentId: 'agent-1', status: 'running' },
      },
    }

    expect(isSessionEventSummary(valid)).toBe(true)
  })

  it('accepts SessionEventSummary with empty event object', () => {
    const valid = {
      timestamp: '2024-03-15T10:31:00Z',
      event: {},
    }

    expect(isSessionEventSummary(valid)).toBe(true)
  })

  it('rejects null', () => {
    expect(isSessionEventSummary(null)).toBe(false)
  })

  it('rejects object with missing timestamp', () => {
    const invalid = {
      event: { type: 'insight' },
    }

    expect(isSessionEventSummary(invalid)).toBe(false)
  })

  it('rejects object with null event', () => {
    const invalid = {
      timestamp: '2024-03-15T10:32:00Z',
      event: null,
    }

    expect(isSessionEventSummary(invalid)).toBe(false)
  })

  it('rejects object with non-object event', () => {
    const invalid = {
      timestamp: '2024-03-15T10:33:00Z',
      event: 'not-an-object',
    }

    expect(isSessionEventSummary(invalid)).toBe(false)
  })
})

describe('SessionEventsHistory type guard', () => {
  it('accepts valid SessionEventsHistory', () => {
    const valid: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:00:00Z',
          event: { type: 'start' },
        },
        {
          timestamp: '2024-03-15T10:05:00Z',
          event: { type: 'agent_update', payload: {} },
        },
      ],
      count: 2,
    }

    expect(isSessionEventsHistory(valid)).toBe(true)
  })

  it('accepts SessionEventsHistory with empty events array', () => {
    const valid = {
      session_id: 'session-456',
      events: [],
      count: 0,
    }

    expect(isSessionEventsHistory(valid)).toBe(true)
  })

  it('rejects null', () => {
    expect(isSessionEventsHistory(null)).toBe(false)
  })

  it('rejects object with missing session_id', () => {
    const invalid = {
      events: [],
      count: 0,
    }

    expect(isSessionEventsHistory(invalid)).toBe(false)
  })

  it('rejects object with non-array events', () => {
    const invalid = {
      session_id: 'session-789',
      events: 'not-an-array',
      count: 0,
    }

    expect(isSessionEventsHistory(invalid)).toBe(false)
  })

  it('rejects object with invalid event in array', () => {
    const invalid = {
      session_id: 'session-999',
      events: [
        { timestamp: '2024-03-15T10:00:00Z', event: {} },
        { timestamp: '2024-03-15T10:05:00Z' }, // missing event
      ],
      count: 2,
    }

    expect(isSessionEventsHistory(invalid)).toBe(false)
  })

  it('rejects object with missing count', () => {
    const invalid = {
      session_id: 'session-111',
      events: [],
    }

    expect(isSessionEventsHistory(invalid)).toBe(false)
  })
})

describe('normalizeSessionSummary', () => {
  it('returns typed SessionSummary for valid input', () => {
    const raw = {
      id: 'session-123',
      ticker: 'AAPL',
      asOfDate: '2024-03-15',
      status: 'completed',
      createdAt: '2024-03-15T10:00:00Z',
      updatedAt: '2024-03-15T11:00:00Z',
    }

    const result = normalizeSessionSummary(raw)

    expect(result).not.toBeNull()
    expect(result).toEqual(raw)
  })

  it('returns null for malformed input', () => {
    const raw = {
      id: 'session-456',
      // missing required fields
    }

    const result = normalizeSessionSummary(raw)

    expect(result).toBeNull()
  })

  it('returns null for null input', () => {
    expect(normalizeSessionSummary(null)).toBeNull()
  })

  it('returns null for undefined input', () => {
    expect(normalizeSessionSummary(undefined)).toBeNull()
  })
})

describe('normalizeSessionEventsHistory', () => {
  it('returns typed SessionEventsHistory for valid input', () => {
    const raw = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:00:00Z',
          event: { type: 'start' },
        },
      ],
      count: 1,
    }

    const result = normalizeSessionEventsHistory(raw)

    expect(result).not.toBeNull()
    expect(result).toEqual(raw)
  })

  it('returns null for malformed input', () => {
    const raw = {
      session_id: 'session-456',
      events: 'not-an-array',
      count: 0,
    }

    const result = normalizeSessionEventsHistory(raw)

    expect(result).toBeNull()
  })

  it('returns null for null input', () => {
    expect(normalizeSessionEventsHistory(null)).toBeNull()
  })
})

describe('enrichSessionWithEvents', () => {
  const baseSummary: SessionSummary = {
    id: 'session-123',
    ticker: 'AAPL',
    asOfDate: '2024-03-15',
    status: 'completed',
    createdAt: '2024-03-15T10:00:00Z',
    updatedAt: '2024-03-15T11:00:00Z',
  }

  it('creates TradingSession from SessionSummary without events', () => {
    const result = enrichSessionWithEvents(baseSummary)

    expect(result).toMatchObject({
      ...baseSummary,
      agents: [],
      insights: [],
    })
    expect(result.decision).toBeUndefined()
    expect(result.risk).toBeUndefined()
  })

  it('creates TradingSession with empty events history', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [],
      count: 0,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result).toMatchObject({
      ...baseSummary,
      agents: [],
      insights: [],
    })
  })

  it('extracts agent snapshots from events', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:10:00Z',
          event: {
            type: 'agent_update',
            payload: {
              id: 'agent-1',
              role: 'analyst',
              status: 'running',
              headline: 'Analyzing AAPL',
              startedAt: '2024-03-15T10:10:00Z',
            },
          },
        },
        {
          timestamp: '2024-03-15T10:20:00Z',
          event: {
            type: 'agent_update',
            payload: {
              id: 'agent-2',
              role: 'researcher',
              status: 'completed',
              headline: 'Research complete',
              startedAt: '2024-03-15T10:15:00Z',
              completedAt: '2024-03-15T10:20:00Z',
            },
          },
        },
      ],
      count: 2,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result.agents).toHaveLength(2)
    expect(result.agents[0]).toMatchObject({
      id: 'agent-1',
      role: 'analyst',
      status: 'running',
    })
    expect(result.agents[1]).toMatchObject({
      id: 'agent-2',
      role: 'researcher',
      status: 'completed',
    })
  })

  it('extracts insights from events', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:30:00Z',
          event: {
            type: 'insight',
            payload: {
              id: 'insight-1',
              agentId: 'agent-1',
              title: 'Strong Buy Signal',
              body: 'Technical indicators show strong momentum',
              confidence: 0.85,
              createdAt: '2024-03-15T10:30:00Z',
            },
          },
        },
      ],
      count: 1,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result.insights).toHaveLength(1)
    expect(result.insights[0]).toMatchObject({
      id: 'insight-1',
      agentId: 'agent-1',
      title: 'Strong Buy Signal',
      confidence: 0.85,
    })
  })

  it('extracts decision from events', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:45:00Z',
          event: {
            type: 'decision',
            payload: {
              action: 'buy',
              conviction: 0.8,
              rationale: 'Strong technical and fundamental indicators',
            },
          },
        },
      ],
      count: 1,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result.decision).toBeDefined()
    expect(result.decision?.action).toBe('buy')
    expect(result.decision?.conviction).toBe(0.8)
    expect(result.decision?.rationale).toBe('Strong technical and fundamental indicators')
  })

  it('extracts risk assessment from events', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:50:00Z',
          event: {
            type: 'risk',
            payload: {
              overall: 'medium',
              summary: 'Moderate volatility expected',
              signals: [
                {
                  id: 'risk-1',
                  category: 'volatility',
                  severity: 'medium',
                  narrative: 'Increased market volatility',
                },
              ],
            },
          },
        },
      ],
      count: 1,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result.risk).toBeDefined()
    expect(result.risk?.overall).toBe('medium')
    expect(result.risk?.summary).toBe('Moderate volatility expected')
    expect(result.risk?.signals).toHaveLength(1)
  })

  it('extracts all data types from mixed events', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:10:00Z',
          event: {
            type: 'agent_update',
            payload: {
              id: 'agent-1',
              role: 'analyst',
              status: 'running',
              headline: 'Analyzing',
              startedAt: '2024-03-15T10:10:00Z',
            },
          },
        },
        {
          timestamp: '2024-03-15T10:20:00Z',
          event: {
            type: 'insight',
            payload: {
              id: 'insight-1',
              agentId: 'agent-1',
              title: 'Insight',
              body: 'Analysis result',
              confidence: 0.9,
              createdAt: '2024-03-15T10:20:00Z',
            },
          },
        },
        {
          timestamp: '2024-03-15T10:30:00Z',
          event: {
            type: 'decision',
            payload: {
              action: 'hold',
              conviction: 0.6,
              rationale: 'Wait for better entry',
            },
          },
        },
        {
          timestamp: '2024-03-15T10:40:00Z',
          event: {
            type: 'risk',
            payload: {
              overall: 'low',
              summary: 'Low risk',
              signals: [],
            },
          },
        },
        {
          timestamp: '2024-03-15T10:50:00Z',
          event: {
            type: 'unknown_type',
            payload: { some: 'data' },
          },
        },
      ],
      count: 5,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result.agents).toHaveLength(1)
    expect(result.insights).toHaveLength(1)
    expect(result.decision).toBeDefined()
    expect(result.risk).toBeDefined()
  })

  it('ignores malformed event payloads', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:10:00Z',
          event: {
            type: 'agent_update',
            payload: {
              // missing required fields
              id: 'agent-1',
            },
          },
        },
        {
          timestamp: '2024-03-15T10:20:00Z',
          event: {
            type: 'insight',
            payload: {
              // missing required fields
              id: 'insight-1',
            },
          },
        },
      ],
      count: 2,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result.agents).toHaveLength(0)
    expect(result.insights).toHaveLength(0)
  })

  it('handles events without payload', () => {
    const eventsHistory: SessionEventsHistory = {
      session_id: 'session-123',
      events: [
        {
          timestamp: '2024-03-15T10:00:00Z',
          event: {
            type: 'start',
          },
        },
        {
          timestamp: '2024-03-15T11:00:00Z',
          event: {
            type: 'end',
          },
        },
      ],
      count: 2,
    }

    const result = enrichSessionWithEvents(baseSummary, eventsHistory)

    expect(result.agents).toHaveLength(0)
    expect(result.insights).toHaveLength(0)
    expect(result.decision).toBeUndefined()
    expect(result.risk).toBeUndefined()
  })

  it('preserves all SessionSummary fields in TradingSession', () => {
    const result = enrichSessionWithEvents(baseSummary)

    expect(result.id).toBe(baseSummary.id)
    expect(result.ticker).toBe(baseSummary.ticker)
    expect(result.asOfDate).toBe(baseSummary.asOfDate)
    expect(result.status).toBe(baseSummary.status)
    expect(result.createdAt).toBe(baseSummary.createdAt)
    expect(result.updatedAt).toBe(baseSummary.updatedAt)
  })
})
