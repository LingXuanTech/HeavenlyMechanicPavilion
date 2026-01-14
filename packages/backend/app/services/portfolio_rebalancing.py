"""Portfolio rebalancing service for automatic portfolio optimization."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ValidationError
from ..db.models import Portfolio, Position
from ..repositories import PortfolioRepository, PositionRepository
from .broker_adapter import BrokerAdapter, MarketPrice
from .execution import ExecutionService

logger = logging.getLogger(__name__)


class PortfolioRebalancingService:
    """Service for automatic portfolio rebalancing."""

    def __init__(
        self,
        broker: BrokerAdapter,
        execution_service: Optional[ExecutionService] = None,
        rebalance_threshold: float = 0.05,  # 5% deviation triggers rebalance
        min_trade_value: float = 100.0,  # Minimum trade value to avoid tiny trades
    ):
        """Initialize rebalancing service.
        
        Args:
            broker: Broker adapter for market data
            execution_service: Service for executing trades
            rebalance_threshold: Threshold for triggering rebalance (e.g., 0.05 = 5%)
            min_trade_value: Minimum value for rebalancing trades
        """
        self.broker = broker
        self.execution_service = execution_service or ExecutionService(broker)
        self.rebalance_threshold = rebalance_threshold
        self.min_trade_value = min_trade_value
        
        logger.info(
            f"Initialized PortfolioRebalancingService with threshold={rebalance_threshold:.1%}, "
            f"min_trade_value=${min_trade_value}"
        )

    async def analyze_portfolio_balance(
        self,
        session: AsyncSession,
        portfolio_id: int,
        target_weights: Dict[str, float],
    ) -> Dict:
        """Analyze portfolio balance against target weights.
        
        Args:
            session: Database session
            portfolio_id: Portfolio ID
            target_weights: Target weights for each symbol (e.g., {"AAPL": 0.25, "GOOGL": 0.25})
            
        Returns:
            Analysis result containing current weights, deviations, and rebalancing actions
        """
        # Validate target weights
        total_weight = sum(target_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValidationError(
                "Target weights must sum to 1.0",
                details={"total_weight": total_weight, "target_weights": target_weights}
            )
        
        # Get portfolio and positions
        portfolio_repo = PortfolioRepository(session)
        position_repo = PositionRepository(session)
        
        portfolio = await portfolio_repo.get(portfolio_id)
        if not portfolio:
            raise ValidationError(
                f"Portfolio {portfolio_id} not found",
                details={"portfolio_id": portfolio_id}
            )
        
        positions = await position_repo.get_by_portfolio(portfolio_id)
        
        # Calculate current portfolio value
        total_value = portfolio.current_capital
        position_values = {}
        
        for position in positions:
            # Get current market price
            market_price = await self.broker.get_market_price(position.symbol)
            position_value = position.quantity * market_price.last
            position_values[position.symbol] = position_value
            total_value += position_value
        
        # Calculate current weights
        current_weights = {
            symbol: value / total_value 
            for symbol, value in position_values.items()
        }
        
        # Add cash weight
        cash_weight = portfolio.current_capital / total_value
        
        # Calculate deviations
        deviations = {}
        rebalancing_needed = False
        
        for symbol, target_weight in target_weights.items():
            current_weight = current_weights.get(symbol, 0.0)
            deviation = current_weight - target_weight
            deviations[symbol] = {
                "current_weight": current_weight,
                "target_weight": target_weight,
                "deviation": deviation,
                "deviation_percent": deviation / target_weight if target_weight > 0 else 0,
            }
            
            # Check if rebalancing is needed
            if abs(deviation) > self.rebalance_threshold:
                rebalancing_needed = True
        
        # Calculate required actions
        actions = await self._calculate_rebalancing_actions(
            session,
            portfolio,
            positions,
            target_weights,
            current_weights,
            total_value,
        )
        
        return {
            "portfolio_id": portfolio_id,
            "total_value": total_value,
            "cash": portfolio.current_capital,
            "cash_weight": cash_weight,
            "current_weights": current_weights,
            "target_weights": target_weights,
            "deviations": deviations,
            "rebalancing_needed": rebalancing_needed,
            "actions": actions,
            "analyzed_at": datetime.utcnow(),
        }

    async def _calculate_rebalancing_actions(
        self,
        session: AsyncSession,
        portfolio: Portfolio,
        positions: List[Position],
        target_weights: Dict[str, float],
        current_weights: Dict[str, float],
        total_value: float,
    ) -> List[Dict]:
        """Calculate rebalancing actions needed.
        
        Args:
            session: Database session
            portfolio: Portfolio
            positions: Current positions
            target_weights: Target weights
            current_weights: Current weights
            total_value: Total portfolio value
            
        Returns:
            List of rebalancing actions
        """
        actions = []
        
        for symbol, target_weight in target_weights.items():
            current_weight = current_weights.get(symbol, 0.0)
            deviation = current_weight - target_weight
            
            # Skip if deviation is within threshold
            if abs(deviation) <= self.rebalance_threshold:
                continue
            
            # Calculate target value and current value
            target_value = total_value * target_weight
            current_value = total_value * current_weight
            value_difference = target_value - current_value
            
            # Skip if trade value is too small
            if abs(value_difference) < self.min_trade_value:
                logger.debug(
                    f"Skipping {symbol}: trade value ${abs(value_difference):.2f} "
                    f"below minimum ${self.min_trade_value}"
                )
                continue
            
            # Get market price
            market_price = await self.broker.get_market_price(symbol)
            current_price = market_price.last
            
            # Calculate quantity to trade
            quantity_to_trade = abs(value_difference) / current_price
            quantity_to_trade = int(quantity_to_trade)  # Round down to whole shares
            
            if quantity_to_trade == 0:
                continue
            
            # Determine action
            action_type = "BUY" if value_difference > 0 else "SELL"
            
            # Get current position
            current_position = next(
                (p for p in positions if p.symbol == symbol), 
                None
            )
            current_quantity = current_position.quantity if current_position else 0
            
            # Validate sell action
            if action_type == "SELL" and quantity_to_trade > current_quantity:
                logger.warning(
                    f"Cannot sell {quantity_to_trade} shares of {symbol}, "
                    f"only {current_quantity} available"
                )
                quantity_to_trade = current_quantity
            
            actions.append({
                "symbol": symbol,
                "action": action_type,
                "quantity": quantity_to_trade,
                "estimated_price": current_price,
                "estimated_value": quantity_to_trade * current_price,
                "current_weight": current_weight,
                "target_weight": target_weight,
                "deviation": deviation,
                "reason": f"Rebalance: {deviation:+.1%} from target",
            })
        
        # Sort actions: SELL first, then BUY (to free up capital)
        actions.sort(key=lambda x: (x["action"] != "SELL", x["symbol"]))
        
        return actions

    async def execute_rebalancing(
        self,
        session: AsyncSession,
        portfolio_id: int,
        target_weights: Dict[str, float],
        dry_run: bool = False,
    ) -> Dict:
        """Execute portfolio rebalancing.
        
        Args:
            session: Database session
            portfolio_id: Portfolio ID
            target_weights: Target weights
            dry_run: If True, only analyze without executing
            
        Returns:
            Rebalancing result
        """
        # Analyze portfolio
        analysis = await self.analyze_portfolio_balance(
            session, portfolio_id, target_weights
        )
        
        if not analysis["rebalancing_needed"]:
            logger.info(f"Portfolio {portfolio_id} is already balanced")
            return {
                "portfolio_id": portfolio_id,
                "rebalancing_needed": False,
                "actions_taken": [],
                "message": "Portfolio is already within target weights",
            }
        
        actions = analysis["actions"]
        
        if dry_run:
            logger.info(
                f"Dry run: Would execute {len(actions)} rebalancing actions "
                f"for portfolio {portfolio_id}"
            )
            return {
                "portfolio_id": portfolio_id,
                "rebalancing_needed": True,
                "dry_run": True,
                "planned_actions": actions,
                "message": f"Dry run: {len(actions)} actions planned",
            }
        
        # Execute actions
        logger.info(
            f"Executing {len(actions)} rebalancing actions for portfolio {portfolio_id}"
        )
        
        actions_taken = []
        for action in actions:
            try:
                trade = await self.execution_service.execute_signal(
                    session=session,
                    portfolio_id=portfolio_id,
                    symbol=action["symbol"],
                    signal=action["action"],
                    current_price=action["estimated_price"],
                    decision_rationale=action["reason"],
                )
                if trade:
                    actions_taken.append({
                        "symbol": action["symbol"],
                        "action": action["action"],
                        "quantity": trade.filled_quantity,
                        "price": trade.average_fill_price,
                        "status": trade.status,
                    })
            except Exception as e:
                logger.error(f"Failed to execute rebalancing action for {action['symbol']}: {e}")
        
        return {
            "portfolio_id": portfolio_id,
            "rebalancing_needed": True,
            "dry_run": False,
            "planned_actions": actions,
            "actions_taken": actions_taken,
            "message": f"Executed {len(actions_taken)}/{len(actions)} rebalancing actions",
        }

    async def calculate_optimal_weights(
        self,
        symbols: List[str],
        strategy: str = "equal_weight",
    ) -> Dict[str, float]:
        """Calculate optimal portfolio weights based on strategy.
        
        Args:
            symbols: List of symbols
            strategy: Rebalancing strategy (equal_weight, market_cap, etc.)
            
        Returns:
            Target weights for each symbol
        """
        if not symbols:
            return {}

        if strategy == "equal_weight":
            # Equal weight for all symbols
            weight = 1.0 / len(symbols)
            return {symbol: weight for symbol in symbols}
        
        elif strategy == "market_cap":
            # Market cap weighted
            from tradingagents.dataflows.interface import route_to_vendor
            import json

            market_caps = {}
            total_market_cap = 0.0

            for symbol in symbols:
                try:
                    # Get fundamental data which includes market cap
                    raw_data = route_to_vendor("get_fundamentals", symbol)
                    
                    # Alpha Vantage returns a JSON string or dict
                    if isinstance(raw_data, str):
                        data = json.loads(raw_data)
                    else:
                        data = raw_data
                    
                    mcap = float(data.get("MarketCapitalization", 0))
                    if mcap <= 0:
                        logger.warning(f"Market cap for {symbol} is 0 or missing, using 1.0 as fallback")
                        mcap = 1.0
                        
                    market_caps[symbol] = mcap
                    total_market_cap += mcap
                except Exception as e:
                    logger.error(f"Failed to get market cap for {symbol}: {e}")
                    market_caps[symbol] = 1.0
                    total_market_cap += 1.0

            if total_market_cap == 0:
                return {symbol: 1.0 / len(symbols) for symbol in symbols}

            return {symbol: mcap / total_market_cap for symbol, mcap in market_caps.items()}
        
        else:
            raise ValidationError(
                f"Unknown rebalancing strategy: {strategy}",
                details={"strategy": strategy, "available": ["equal_weight", "market_cap"]}
            )