# Real-Time Trading Dashboard

## Overview

The real-time trading dashboard provides a comprehensive view of portfolio performance, trading signals, execution history, and agent activity through WebSocket/SSE connections.

## Features

### 1. Portfolio Overview
- **Live Portfolio Value**: Real-time total portfolio value with P&L tracking
- **Cash Position**: Available cash for trading
- **Holdings Display**: List of all current positions with:
  - Symbol and position type (LONG/SHORT)
  - Quantity and average cost
  - Current market value
  - Unrealized P&L with percentage change
- **Daily P&L**: Today's profit/loss with percentage
- **Total P&L**: Cumulative profit/loss

### 2. Live Signal Feed
- **Real-time Signals**: Stream of trading signals as they are generated
- **Signal Details**:
  - Symbol and signal type (BUY/SELL/HOLD)
  - Signal strength/confidence
  - Price at signal generation
  - Source of the signal
  - Rationale and supporting indicators
- **Filtering**: Filter signals by type (All/Buy/Sell/Hold)
- **Auto-scroll**: Newest signals appear at the top

### 3. Trade Execution Timeline
- **Execution History**: Chronological view of all trades
- **Trade Details**:
  - Symbol and trade type (BUY/SELL)
  - Quantity and execution price
  - Total cost
  - Status (executed/pending/failed/cancelled)
  - Decision rationale and confidence score
- **Visual Timeline**: Timeline visualization with status indicators
- **Filtering**: Filter by execution status

### 4. Agent Activity Stream
- **Agent Updates**: Real-time activity from all trading agents
- **Agent Types**:
  - Analyst (market analysis)
  - Researcher (research and insights)
  - Trader (trade execution)
  - Risk Manager (risk checks)
  - Portfolio Manager (portfolio management)
- **Activity Types**:
  - Analysis
  - Signal generation
  - Trade execution
  - Risk checks
  - Insights
- **Filtering**: Filter by agent role
- **Status Indicators**: Visual status for each activity (started/in_progress/completed/failed)

## Dashboard Controls

### Time Range Selection
- Last Hour
- Last 4 Hours
- Last Day
- Last Week
- Last Month
- All Time

### View Modes
- **Overview**: All components in a single view
- **Detailed**: Tabbed view with one component at a time

## Technical Implementation

### Real-time Data
- **SSE (Server-Sent Events)**: Used for real-time data streaming
- **Auto-reconnect**: Automatic reconnection on connection loss
- **Connection Status**: Visual indicators for connection state

### Data Hooks
- `useRealtimePortfolio`: Portfolio updates
- `useRealtimeSignals`: Trading signals
- `useRealtimeTrades`: Trade executions
- `useRealtimeAgentActivity`: Agent activity

### UI Components
- Built with shadcn/ui primitives
- Responsive layout for all screen sizes
- Dark mode support (follows system theme)
- Accessible keyboard navigation
- ARIA labels for screen readers

### Charting
- Recharts library for portfolio charts
- Live updating data visualization
- Responsive charts that adapt to container size

## Configuration

Create a `.env.local` file in the frontend package:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend Requirements

The dashboard expects the following SSE endpoints:

- `GET /api/stream/portfolio/{portfolioId}` - Portfolio updates
- `GET /api/stream/signals` - Trading signals
- `GET /api/stream/signals/{portfolioId}` - Portfolio-specific signals
- `GET /api/stream/trades/{portfolioId}` - Trade executions
- `GET /api/stream/agent-activity` - Agent activity
- `GET /api/stream/agent-activity/{sessionId}` - Session-specific activity

Each endpoint should emit events in the following format:

```json
{
  "type": "portfolio_update" | "signal" | "trade" | "agent_activity" | "error" | "heartbeat",
  "data": { ... }
}
```

## Accessibility

- All interactive elements are keyboard accessible
- Proper ARIA labels and roles
- Focus management for modals and popups
- Color contrast meets WCAG 2.1 AA standards
- Screen reader friendly

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance

- Efficient re-rendering with React hooks
- Virtualized scrolling for large lists
- Debounced filters and controls
- Lazy loading for heavy components
