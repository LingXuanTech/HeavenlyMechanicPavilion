# Trading Execution and Risk Management Services

This document describes the automated trading execution and risk management services that convert agent signals into executed orders with comprehensive risk controls.

## Overview

The execution and risk management system consists of several integrated components:

1. **Execution Pipeline** - Converts trading signals into orders with position sizing
2. **Risk Management** - VaR calculation, stop-loss/take-profit, portfolio constraints
3. **Broker Adapters** - Simulated and live broker interfaces
4. **Trading Sessions** - Manage paper and live trading sessions
5. **Persistence** - Track orders, fills, and lifecycle events

## Architecture

```
┌─────────────────────┐
│ TradingAgentsGraph  │
│   (Signals)         │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────┐
│ ExecutionIntegration │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐         ┌─────────────────────┐
│  ExecutionService    │────────▶│  BrokerAdapter      │
└──────────┬───────────┘         │  - Simulated        │
           │                     │  - Live (future)    │
           │                     └─────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌───────────┐  ┌────────────────┐
│ Position  │  │ Risk          │
│ Sizing    │  │ Management    │
└───────────┘  └────────────────┘
    │             │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Database    │
    │ - Trades    │
    │ - Positions │
    │ - RiskMetrics│
    └─────────────┘
```

## Core Components

### 1. Execution Service (`app/services/execution.py`)

The main service that orchestrates trade execution:

```python
from app.services import ExecutionService, SimulatedBroker

# Initialize
broker = SimulatedBroker(initial_capital=100000.0)
execution_service = ExecutionService(broker)

# Execute a signal
trade = await execution_service.execute_signal(
    session=db_session,
    portfolio_id=1,
    symbol="AAPL",
    signal="BUY",
    current_price=150.0,
    decision_rationale="Strong buy signal",
    confidence_score=0.85,
)
```

**Key Features:**
- Converts BUY/SELL/HOLD signals into executable orders
- Automatic position sizing based on portfolio value
- Pre-execution risk checks
- Position tracking and P&L calculation
- Commission and slippage modeling

### 2. Position Sizing Service (`app/services/position_sizing.py`)

Calculates order quantities using various methods:

**Available Methods:**
- `FIXED_DOLLAR` - Fixed dollar amount per position
- `FIXED_PERCENTAGE` - Fixed percentage of portfolio (default 5%)
- `RISK_BASED` - Based on stop-loss distance and max risk per trade
- `VOLATILITY_BASED` - Inverse volatility weighting
- `KELLY_CRITERION` - Kelly criterion with fractional Kelly

```python
from app.services import PositionSizingService, PositionSizingMethod

sizing = PositionSizingService(
    method=PositionSizingMethod.RISK_BASED,
    risk_per_trade=0.02,  # Max 2% risk per trade
    max_position_size=0.20,  # Max 20% per position
)

quantity = sizing.calculate_quantity(
    symbol="AAPL",
    action="BUY",
    current_price=150.0,
    portfolio_value=100000.0,
    stop_loss_price=135.0,  # For risk-based sizing
)
```

### 3. Risk Management Service (`app/services/risk_management.py`)

Comprehensive risk analysis and control:

**Risk Metrics:**
- Value at Risk (VaR) at 95% and 99% confidence
- Portfolio volatility and Sharpe ratio
- Maximum drawdown
- Position concentration
- Exposure metrics (long, short, net)

**Risk Controls:**
- Maximum position size limits
- Portfolio exposure limits
- Stop-loss and take-profit rules
- Portfolio rebalancing

```python
from app.services import RiskManagementService, RiskConstraints

constraints = RiskConstraints(
    max_position_weight=0.20,
    max_portfolio_exposure=1.0,
    default_stop_loss_pct=0.10,
    default_take_profit_pct=0.20,
)

risk_service = RiskManagementService(constraints=constraints)

# Calculate diagnostics
diagnostics = await risk_service.calculate_diagnostics(
    portfolio_id=1,
    positions=positions,
    current_prices={"AAPL": 150.0, "MSFT": 380.0},
)

# Check stop-loss
if risk_service.check_stop_loss(position, current_price):
    # Trigger exit
    pass
```

### 4. Broker Adapters (`app/services/broker_adapter.py`)

Abstract interface for order execution:

**SimulatedBroker** - Paper trading with realistic simulation:
- Configurable commission and slippage
- Market and limit order types
- Instant execution for market orders
- Capital tracking

```python
from app.services import SimulatedBroker, OrderRequest, OrderAction, OrderType

broker = SimulatedBroker(
    initial_capital=100000.0,
    commission_per_trade=0.0,
    slippage_percent=0.001,  # 0.1% slippage
)

order = OrderRequest(
    symbol="AAPL",
    action=OrderAction.BUY,
    quantity=100,
    order_type=OrderType.MARKET,
)

response = await broker.submit_order(order)
```

**Future: Live Broker** - Interface ready for live trading integration

### 5. Trading Session Service (`app/services/trading_session.py`)

Manages trading sessions with full lifecycle:

```python
from app.services import TradingSessionService

session_service = TradingSessionService()

# Start a paper trading session
trading_session = await session_service.start_session(
    session=db_session,
    portfolio_id=1,
    session_type="PAPER",
    name="My Trading Session",
    stop_loss_percentage=0.10,
    take_profit_percentage=0.20,
)

# Get execution service for the session
execution = session_service.get_execution_service(trading_session.id)

# Stop the session
await session_service.stop_session(db_session, trading_session.id)
```

## Database Models

### TradingSession
Tracks live and paper trading sessions:
- Session type (PAPER/LIVE)
- Status (ACTIVE/STOPPED/COMPLETED)
- Risk parameters (stop-loss, take-profit, limits)
- Performance metrics (P&L, win rate)

### RiskMetrics
Time-series risk measurements:
- VaR at multiple confidence levels
- Portfolio metrics (volatility, Sharpe, drawdown)
- Concentration and exposure metrics
- Timestamp for historical analysis

### Trade
Order records with full lifecycle:
- Order details (symbol, action, quantity, type)
- Status (PENDING/FILLED/PARTIAL/CANCELLED/REJECTED)
- Execution details (fill price, quantity)
- Agent decision metadata (rationale, confidence)

### Execution
Individual fill records:
- Linked to parent trade
- Execution price and quantity
- Commission and fees
- Exchange information

### Position
Current holdings:
- Quantity and average cost basis
- Current price and unrealized P&L
- Position type (LONG/SHORT)
- Entry date

## API Endpoints

### Start Trading Session
```http
POST /trading/sessions/start
Content-Type: application/json

{
  "portfolio_id": 1,
  "session_type": "PAPER",
  "name": "My Trading Session",
  "max_position_size": 0.20,
  "stop_loss_percentage": 0.10,
  "take_profit_percentage": 0.20,
  "position_sizing_method": "RISK_BASED"
}
```

### Stop Trading Session
```http
POST /trading/sessions/{session_id}/stop
```

### Execute Trading Signal
```http
POST /trading/execute
Content-Type: application/json

{
  "portfolio_id": 1,
  "symbol": "AAPL",
  "signal": "BUY",
  "current_price": 150.0,
  "decision_rationale": "Strong buy signal from analysts",
  "confidence_score": 0.85,
  "session_id": 1
}
```

### Force Exit Position
```http
POST /trading/positions/exit
Content-Type: application/json

{
  "portfolio_id": 1,
  "symbol": "AAPL",
  "reason": "Risk limit breach"
}
```

### Get Risk Diagnostics
```http
GET /trading/risk/diagnostics/{portfolio_id}?session_id={session_id}
```

Response:
```json
{
  "portfolio_id": 1,
  "portfolio_value": 105000.0,
  "var_1day_95": -1250.0,
  "var_1day_99": -2100.0,
  "portfolio_volatility": 0.18,
  "sharpe_ratio": 1.2,
  "max_drawdown": 0.05,
  "largest_position_weight": 0.18,
  "number_of_positions": 5,
  "total_exposure": 98000.0,
  "long_exposure": 98000.0,
  "short_exposure": 0.0,
  "net_exposure": 98000.0,
  "warnings": []
}
```

### Get Portfolio State
```http
GET /trading/portfolio/{portfolio_id}/state
```

Response:
```json
{
  "portfolio": {
    "id": 1,
    "name": "My Portfolio",
    "current_capital": 52000.0
  },
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 100,
      "average_cost": 150.0,
      "current_price": 155.0,
      "unrealized_pnl": 500.0
    }
  ],
  "total_value": 105000.0,
  "total_unrealized_pnl": 5000.0,
  "total_realized_pnl": 0.0
}
```

## Integration with TradingAgentsGraph

The execution services integrate seamlessly with the existing graph:

```python
from tradingagents.graph import TradingAgentsGraph
from tradingagents.graph.execution_integration import ExecutionIntegration
from app.services import TradingSessionService

# Set up graph
graph = TradingAgentsGraph(selected_analysts=["market", "news"])

# Start trading session
session_service = TradingSessionService()
trading_session = await session_service.start_session(
    session=db_session,
    portfolio_id=portfolio_id,
    session_type="PAPER",
)

# Get execution service
execution_service = session_service.get_execution_service(trading_session.id)

# Create integration
integration = ExecutionIntegration(
    execution_service=execution_service,
    session_id=trading_session.id,
)

# Run graph and execute decision
final_state, processed_signal = graph.propagate("AAPL", "2024-01-01")

# Execute the decision
trade = await integration.execute_graph_decision(
    db_session=db_session,
    portfolio_id=portfolio_id,
    symbol="AAPL",
    decision=processed_signal,
    current_price=150.0,
    state=final_state,
)
```

## Risk Management Best Practices

1. **Position Sizing**
   - Use risk-based sizing to limit loss per trade
   - Never exceed max position size limits
   - Consider volatility when sizing positions

2. **Stop-Loss Rules**
   - Always set stop-loss for new positions
   - Use trailing stops to protect profits
   - Review and adjust stops regularly

3. **Portfolio Constraints**
   - Monitor position concentration
   - Limit total portfolio exposure
   - Maintain adequate cash reserves

4. **VaR Monitoring**
   - Track VaR trends over time
   - Set maximum VaR thresholds
   - Reduce exposure when VaR increases

5. **Regular Reviews**
   - Calculate risk metrics daily
   - Review triggered stops/profits
   - Rebalance when concentration is high

## Testing and Validation

Run the example script to test all components:

```bash
cd /home/engine/project/packages/backend
python examples/execution_example.py
```

Or use the API:

```bash
# Start the server
uvicorn app.main:app --reload

# Test endpoints
curl -X POST http://localhost:8000/trading/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id": 1, "session_type": "PAPER"}'
```

## Future Enhancements

1. **Live Broker Integration**
   - Interactive Brokers adapter
   - Alpaca adapter
   - Other broker APIs

2. **Advanced Risk Models**
   - Monte Carlo VaR
   - Conditional VaR (CVaR)
   - Stress testing scenarios

3. **Portfolio Optimization**
   - Mean-variance optimization
   - Risk parity allocation
   - Factor-based allocation

4. **Performance Analytics**
   - Attribution analysis
   - Risk-adjusted returns
   - Benchmark comparison

5. **Real-time Monitoring**
   - WebSocket updates
   - Alert notifications
   - Dashboard integration

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review example scripts in `examples/`
3. See test cases for usage patterns
